import argparse
import asyncio
import logging
import os
import sys

import aiohttp

# Ensure src/ is on sys.path for direct module imports
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from lib.api_client import MyRideAPIClient
from lib.auth import AuthManager
from lib.config import settings
from lib.db import AsyncSessionLocal, get_recent_bus_locations, init_db, save_bus_location, save_student
from lib.scheduler import get_active_window_info
from lib.signalr_client import SignalRClient
from web.server import start_web_server

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("myride.main")


async def cmd_test_auth(refresh_token: str = None):
    print("=== TESTING MYRIDE AUTHENTICATION & REST API ===")
    auth = AuthManager(refresh_token=refresh_token)
    api = MyRideAPIClient()

    try:
        token = await auth.get_valid_access_token()
        print(f"[SUCCESS] Obtained valid Access Token (starts with {token[:15]}...)")
    except Exception as e:
        print(f"[ERROR] Authentication failed: {e}")
        return None, None

    user_info = await api.get_user_info(token)
    print(f"[SUCCESS] User Name: {user_info.get('name')}, Email: {user_info.get('email')}")

    groups = user_info.get("groups", [])
    if not groups:
        print("[ERROR] No district groups found in user profile.")
        return token, None

    tenant_id = groups[0].get("groupGuid")
    district_name = groups[0].get("name")
    print(f"[SUCCESS] Tenant ID (District GUID): {tenant_id}")
    print(f"[SUCCESS] District Name: {district_name}")

    students = await api.get_student_info(token, tenant_id)
    print(f"[SUCCESS] Retrieved {len(students)} student record(s):")
    for s in students:
        runs = s.get("runInfo", [])
        bus_no = runs[0].get("assetUniqueId") if runs else "N/A"
        print(
            f"  - Student: {s.get('firstName')} {s.get('lastName')}, Location: {s.get('locationName')}, Bus #: {bus_no}"
        )

    return token, tenant_id


async def cmd_test_ws(refresh_token: str = None, duration: int = 30):
    token, tenant_id = await cmd_test_auth(refresh_token=refresh_token)
    if not token or not tenant_id:
        return

    print("\n=== TESTING SIGNALR WEBSOCKET NEGOTIATION & CONNECTION ===")
    api = MyRideAPIClient()

    async with aiohttp.ClientSession() as session:
        negotiate_data = await api.negotiate_signalr(token, tenant_id, session=session)
        connection_token = negotiate_data.get("connectionToken") or negotiate_data.get("connectionId")
        print(f"[SUCCESS] SignalR Connection Token: {connection_token[:20]}...")

        await init_db()

        async def handle_location(data: dict, raw_payload: str):
            async with AsyncSessionLocal() as db_sess:
                record = await save_bus_location(db_sess, data, raw_payload)
                print(
                    f"[SAVED DB #{record.id}] Bus {record.asset_unique_id} -> Lat: {record.latitude}, Lon: {record.longitude}, Speed: {record.speed} mph"
                )

        ws_client = SignalRClient(
            tenant_id=tenant_id, connection_token=connection_token, access_token=token, on_location=handle_location
        )

        print(f"Listening for WebSocket location updates for {duration} seconds...")
        await ws_client.connect_and_listen(session=session, max_seconds=duration)


async def cmd_run_daemon(refresh_token: str = None, ignore_schedule: bool = False, enable_web: bool = True):
    print("=== STARTING MYRIDE TRACKER DAEMON & WEB SERVER ===")
    await init_db()

    if ignore_schedule:
        settings.myride_ignore_schedule = True

    # Start Web Dashboard Server if enabled
    if enable_web:
        await start_web_server(settings.web_host, settings.web_port)
        print(
            f"[WEB DASHBOARD] Open http://localhost:{settings.web_port} in your browser to view the bus map & history!"
        )

    auth = AuthManager(refresh_token=refresh_token)
    api = MyRideAPIClient()

    retry_delay = 5
    while True:
        try:
            is_active, time_str, status_msg = get_active_window_info()

            if not is_active:
                logger.info("[STANDBY] Current Time: %s. %s. Checking again in 30 seconds...", time_str, status_msg)
                await asyncio.sleep(30)
                continue

            logger.info("[ACTIVE WINDOW] Time: %s. Initiating bus tracker WebSocket stream...", time_str)
            token = await auth.get_valid_access_token()
            user_info = await api.get_user_info(token)
            tenant_id = user_info["groups"][0]["groupGuid"]

            # Store students in DB
            students = await api.get_student_info(token, tenant_id)
            async with AsyncSessionLocal() as db_sess:
                for st in students:
                    await save_student(db_sess, st, tenant_id)

            async with aiohttp.ClientSession() as session:
                negotiate_data = await api.negotiate_signalr(token, tenant_id, session=session)
                conn_token = negotiate_data.get("connectionToken") or negotiate_data.get("connectionId")

                async def on_loc(data: dict, raw: str):
                    async with AsyncSessionLocal() as db_sess:
                        await save_bus_location(db_sess, data, raw)

                client = SignalRClient(
                    tenant_id=tenant_id, connection_token=conn_token, access_token=token, on_location=on_loc
                )

                print("[DAEMON] WebSocket connected. Streaming bus locations to database...")
                await client.connect_and_listen(session=session)
            retry_delay = 5
        except asyncio.CancelledError:
            print("[DAEMON] Stopping daemon service...")
            break
        except Exception as e:
            logger.error("Daemon error: %s. Retrying in %d seconds...", e, retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)


async def cmd_web(host: str = None, port: int = None):
    await init_db()
    host = host or settings.web_host
    port = port or settings.web_port
    print(f"=== STARTING MYRIDE WEB DASHBOARD AT http://localhost:{port} ===")
    await start_web_server(host, port)
    await asyncio.Event().wait()


async def cmd_history():
    await init_db()
    async with AsyncSessionLocal() as session:
        records = await get_recent_bus_locations(session, limit=20)
        print(f"=== RECENT STORED BUS LOCATIONS ({len(records)} RECORDS) ===")
        for r in records:
            print(
                f"[{r.id}] Bus {r.asset_unique_id} | Time: {r.log_time} | Lat: {r.latitude}, Lon: {r.longitude} | Speed: {r.speed} mph | Recv: {r.received_at}"
            )


def main():
    parser = argparse.ArgumentParser(description="MyRide K12 Bus Tracker, Web Dashboard & SignalR Logger")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    auth_parser = subparsers.add_parser("test-auth", help="Test authentication and user/student retrieval")
    auth_parser.add_argument("--token", help="MyRide refresh token (optional override)")

    ws_parser = subparsers.add_parser("test-ws", help="Test SignalR WebSocket connection & location streaming")
    ws_parser.add_argument("--token", help="MyRide refresh token (optional override)")
    ws_parser.add_argument("--duration", type=int, default=30, help="Duration to listen in seconds")

    run_parser = subparsers.add_parser("run", help="Start continuous daemon logging service & web dashboard")
    run_parser.add_argument("--token", help="MyRide refresh token (optional override)")
    run_parser.add_argument(
        "--ignore-schedule", action="store_true", help="Bypass active time window check and run continuous stream"
    )
    run_parser.add_argument("--no-web", action="store_true", help="Disable embedded web server dashboard")

    web_parser = subparsers.add_parser("web", help="Start standalone web dashboard server")
    web_parser.add_argument("--host", default=settings.web_host, help="Web server host")
    web_parser.add_argument("--port", type=int, default=settings.web_port, help="Web server port")

    subparsers.add_parser("history", help="View recent bus location records stored in SQLite database")

    args = parser.parse_args()

    if args.command == "test-auth":
        asyncio.run(cmd_test_auth(refresh_token=args.token))
    elif args.command == "test-ws":
        asyncio.run(cmd_test_ws(refresh_token=args.token, duration=args.duration))
    elif args.command == "run":
        asyncio.run(
            cmd_run_daemon(refresh_token=args.token, ignore_schedule=args.ignore_schedule, enable_web=not args.no_web)
        )
    elif args.command == "web":
        asyncio.run(cmd_web(host=args.host, port=args.port))
    elif args.command == "history":
        asyncio.run(cmd_history())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
