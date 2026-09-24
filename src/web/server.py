import os
import logging
from aiohttp import web
from sqlalchemy import select, func
from lib.config import settings
from lib.scheduler import get_active_window_info, is_bus_active_time
from lib.db import AsyncSessionLocal, get_recent_bus_locations, get_route_dates, get_route_by_date, get_or_create_daily_route
from lib.models import BusLocation, StudentRecord

logger = logging.getLogger("myride.web")

async def handle_index(request):
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return web.FileResponse(index_file)
    return web.Response(text="MyRide K12 Tracker Web Server is Running.")

async def handle_api_status(request):
    is_active, time_str, msg = get_active_window_info()

    async with AsyncSessionLocal() as session:
        # Get latest bus location point
        stmt = select(BusLocation).order_by(BusLocation.id.desc()).limit(1)
        res = await session.execute(stmt)
        latest_loc = res.scalar_one_or_none()

        # Get student info
        stmt_st = select(StudentRecord).limit(1)
        res_st = await session.execute(stmt_st)
        student = res_st.scalar_one_or_none()

    latest_loc_dict = None
    if latest_loc:
        latest_loc_dict = {
            "id": latest_loc.id,
            "asset_unique_id": latest_loc.asset_unique_id,
            "asset_id": latest_loc.asset_id,
            "latitude": latest_loc.latitude,
            "longitude": latest_loc.longitude,
            "heading": latest_loc.heading,
            "speed": latest_loc.speed,
            "log_time": latest_loc.log_time,
            "received_at": latest_loc.received_at.isoformat() if latest_loc.received_at else None,
        }

    student_dict = None
    if student:
        student_dict = {
            "student_id": student.student_id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "location_name": student.location_name,
            "active_vehicle": student.active_vehicle,
        }

    payload = {
        "is_active_window": is_active,
        "ignore_schedule": settings.myride_ignore_schedule,
        "current_time_et": time_str,
        "status_message": msg,
        "latest_location": latest_loc_dict,
        "student": student_dict,
    }
    return web.json_response(payload)

async def handle_api_locations(request):
    try:
        limit = int(request.query.get("limit", 100))
        limit = min(max(1, limit), 1000)
    except ValueError:
        limit = 100

    async with AsyncSessionLocal() as session:
        records = await get_recent_bus_locations(session, limit=limit)

    items = [
        {
            "id": r.id,
            "asset_unique_id": r.asset_unique_id,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "heading": r.heading,
            "speed": r.speed,
            "log_time": r.log_time,
            "received_at": r.received_at.isoformat() if r.received_at else None,
        }
        for r in records
    ]
    return web.json_response(items)

async def handle_api_stats(request):
    async with AsyncSessionLocal() as session:
        count_stmt = select(func.count(BusLocation.id))
        count_res = await session.execute(count_stmt)
        total_points = count_res.scalar() or 0

        max_speed_stmt = select(func.max(BusLocation.speed))
        max_speed_res = await session.execute(max_speed_stmt)
        max_speed = max_speed_res.scalar() or 0.0

        avg_speed_stmt = select(func.avg(BusLocation.speed))
        avg_speed_res = await session.execute(avg_speed_stmt)
        avg_speed = round(avg_speed_res.scalar() or 0.0, 1)

    return web.json_response({
        "total_points": total_points,
        "max_speed": max_speed,
        "avg_speed": avg_speed,
    })

async def handle_api_route_dates(request):
    async with AsyncSessionLocal() as session:
        dates = await get_route_dates(session)
    return web.json_response(dates)

async def handle_api_route_by_date(request):
    date_str = request.query.get("date")
    async with AsyncSessionLocal() as session:
        if not date_str:
            dates = await get_route_dates(session)
            if dates:
                date_str = dates[0]
            else:
                return web.json_response({"date": None, "total_points": 0, "distance_miles": 0.0, "vector_coords": [], "locations": []})
        
        route_data = await get_or_create_daily_route(session, date_str)

    items = [
        {
            "id": r.id,
            "asset_unique_id": r.asset_unique_id,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "heading": r.heading,
            "speed": r.speed,
            "log_time": r.log_time,
            "received_at": r.received_at.isoformat() if r.received_at else None,
        }
        for r in route_data.get("locations", [])
    ]
    return web.json_response({
        "date": date_str,
        "total_points": len(items),
        "distance_miles": route_data.get("distance_miles", 0.0),
        "vector_coords": route_data.get("vector_coords", []),
        "locations": items
    })

def create_web_app():
    app = web.Application()
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    os.makedirs(static_dir, exist_ok=True)

    app.router.add_get("/", handle_index)
    app.router.add_get("/api/status", handle_api_status)
    app.router.add_get("/api/locations", handle_api_locations)
    app.router.add_get("/api/stats", handle_api_stats)
    app.router.add_get("/api/routes/dates", handle_api_route_dates)
    app.router.add_get("/api/routes/by-date", handle_api_route_by_date)
    app.router.add_static("/static/", static_dir, name="static")

    return app

async def start_web_server(host: str = None, port: int = None):
    host = host or settings.web_host
    port = port or settings.web_port
    app = create_web_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("MyRide Web Dashboard running at http://%s:%s", host if host != "0.0.0.0" else "localhost", port)
    return runner
