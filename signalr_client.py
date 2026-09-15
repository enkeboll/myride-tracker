import json
import asyncio
import logging
import aiohttp
from typing import Optional, Callable, Awaitable
from config import settings

logger = logging.getLogger("myride.signalr")

RECORD_SEPARATOR = "\x1e"

DEFAULT_WS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "Origin": "https://myridek12.tylerapp.com",
    "Referer": "https://myridek12.tylerapp.com/",
    "x-client-language": "en",
    "x-client-version": "2026.3.35+faa0e3",
    "x-device-type": "browser",
    "x-requested-with": "XMLHttpRequest",
    "x-signalr-user-agent": "Microsoft SignalR/10.0 (10.0.0+b0f34d51fccc69fd334253924abd8d6853fad7aa; Unknown OS; .NET; .NET 10.0.11)",
}

class SignalRClient:
    def __init__(
        self,
        tenant_id: str,
        connection_token: str,
        access_token: str,
        on_location: Optional[Callable[[dict, str], Awaitable[None]]] = None,
        ws_base_url: Optional[str] = None
    ):
        self.tenant_id = tenant_id
        self.connection_token = connection_token
        self.access_token = access_token
        self.on_location = on_location
        self.ws_base_url = ws_base_url or settings.ws_base_url
        self.websocket = None
        self.is_running = False
        self._ping_task = None

    def build_ws_url(self) -> str:
        url = (
            f"{self.ws_base_url}/livevehiclehub"
            f"?x-tenant-id={self.tenant_id}"
            f"&id={self.connection_token}"
            f"&access_token={self.access_token}"
        )
        return url

    async def connect_and_listen(self, session: Optional[aiohttp.ClientSession] = None, max_seconds: Optional[int] = None):
        ws_url = self.build_ws_url()
        logger.info("Connecting to SignalR WebSocket: %s", ws_url.split("access_token=")[0] + "access_token=redacted")

        close_session = False
        if session is None:
            session = aiohttp.ClientSession(headers=DEFAULT_WS_HEADERS)
            close_session = True

        try:
            async with session.ws_connect(ws_url, headers=DEFAULT_WS_HEADERS) as ws:
                self.websocket = ws
                self.is_running = True

                # 1. Send SignalR Handshake
                handshake = json.dumps({"protocol": "json", "version": 1}) + RECORD_SEPARATOR
                await ws.send_str(handshake)
                logger.info("Sent SignalR handshake.")

                # 2. Receive Handshake Response
                msg = await ws.receive()
                resp_text = msg.data.rstrip(RECORD_SEPARATOR) if hasattr(msg, "data") and isinstance(msg.data, str) else ""
                logger.info("Received SignalR handshake response: %s", resp_text)

                # Start ping background task
                self._ping_task = asyncio.create_task(self._ping_loop())

                buffer = ""
                start_time = asyncio.get_event_loop().time()

                try:
                    while self.is_running:
                        if max_seconds and (asyncio.get_event_loop().time() - start_time) >= max_seconds:
                            logger.info("Reached maximum duration of %s seconds. Disconnecting.", max_seconds)
                            break

                        try:
                            msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                        except asyncio.TimeoutError:
                            continue

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            buffer += msg.data
                            while RECORD_SEPARATOR in buffer:
                                record, buffer = buffer.split(RECORD_SEPARATOR, 1)
                                if record:
                                    await self._handle_record(record)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            logger.warning("WebSocket closed or error: %s", msg)
                            break
                finally:
                    self.is_running = False
                    if self._ping_task:
                        self._ping_task.cancel()
        finally:
            if close_session:
                await session.close()

    async def _handle_record(self, record_str: str):
        try:
            data = json.loads(record_str)
        except json.JSONDecodeError:
            logger.warning("Failed to decode SignalR record: %s", record_str)
            return

        msg_type = data.get("type")
        
        # Ping frame
        if msg_type == 6:
            logger.debug("Received SignalR ping (type 6)")
            return

        # Target invocation message
        if msg_type == 1:
            target = data.get("target")
            args = data.get("arguments", [])
            logger.info("Received SignalR Invocation target='%s' with %d args", target, len(args))
            if target == "NewLocation" and args:
                location_data = args[0]
                logger.info(
                    "Bus Location Update -> Asset: %s, LogTime: %s, Lat: %s, Lon: %s, Speed: %s mph",
                    location_data.get("assetUniqueId"),
                    location_data.get("logTime"),
                    location_data.get("latitude"),
                    location_data.get("longitude"),
                    location_data.get("speed")
                )
                if self.on_location:
                    await self.on_location(location_data, record_str)

    async def _ping_loop(self):
        """Sends periodic SignalR ping frames (type 6) to keep connection active."""
        try:
            while self.is_running:
                await asyncio.sleep(15)
                if self.websocket and self.is_running:
                    ping_msg = json.dumps({"type": 6}) + RECORD_SEPARATOR
                    await self.websocket.send_str(ping_msg)
                    logger.debug("Sent SignalR ping frame")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning("Error in ping loop: %s", e)

    def stop(self):
        self.is_running = False
