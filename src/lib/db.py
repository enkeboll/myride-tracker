import json
import os
from datetime import datetime, timezone

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, BusLocation, StudentRecord

# Ensure target SQLite directory exists if a file path is specified
if "sqlite" in settings.db_url:
    db_path = settings.db_url.split("///")[-1]
    if db_path and not db_path.startswith(":memory:"):
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

engine = create_async_engine(
    settings.db_url,
    echo=False,
    future=True,
)

# Enable WAL mode for SQLite to optimize local/NAS file writing concurrency
if settings.db_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.close()


AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Ensure column migrations for existing SQLite tables
        for col_name, col_type in [
            ("home_lat", "FLOAT"),
            ("home_lon", "FLOAT"),
            ("home_address", "VARCHAR(200)"),
            ("school_lat", "FLOAT"),
            ("school_lon", "FLOAT"),
            ("stop_lat", "FLOAT"),
            ("stop_lon", "FLOAT"),
            ("stop_address", "VARCHAR(200)"),
        ]:
            try:
                await conn.execute(text(f"ALTER TABLE students ADD COLUMN {col_name} {col_type}"))
            except Exception:
                pass


async def save_bus_location(session: AsyncSession, data: dict, raw_payload: str) -> BusLocation:
    record = BusLocation(
        asset_unique_id=str(data.get("assetUniqueId", "unknown")),
        asset_id=data.get("assetId"),
        log_time=str(data.get("logTime", "")),
        latitude=float(data.get("latitude", 0.0)),
        longitude=float(data.get("longitude", 0.0)),
        heading=float(data["heading"]) if data.get("heading") is not None else None,
        speed=float(data["speed"]) if data.get("speed") is not None else None,
        vendor_id=data.get("vendorId"),
        visible_run_name=data.get("visibleRunName"),
        received_at=datetime.now(timezone.utc),
        raw_payload=raw_payload,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def save_student(session: AsyncSession, data: dict, tenant_id: str = None) -> StudentRecord:
    student_id = data.get("studentId")
    active_bus = None
    runs = data.get("runInfo", [])
    if runs and isinstance(runs, list):
        active_bus = runs[0].get("assetUniqueId") or runs[0].get("rolloutBusNumber")

    home_addr = data.get("homeAddress", {}) or {}
    h_lat = home_addr.get("latitude")
    h_lon = home_addr.get("longitude")
    h_parts = [
        p
        for p in [home_addr.get("addrLine1"), home_addr.get("city"), home_addr.get("state"), home_addr.get("zip")]
        if p
    ]
    h_addr_str = ", ".join(h_parts) if h_parts else None

    sch_lat = None
    sch_lon = None
    st_lat = None
    st_lon = None
    st_addr_str = None

    if runs and isinstance(runs, list):
        for run in runs:
            stops = run.get("stopsInfo", [])
            for s in stops:
                action = s.get("actionType")
                loc_name = s.get("locationName")
                if loc_name and not sch_lat:
                    sch_lat = s.get("stopLat")
                    sch_lon = s.get("stopLong")
                if action in ("Dropoff", "Pickup") and not st_lat:
                    st_lat = s.get("stopLat")
                    st_lon = s.get("stopLong")
                    st_addr_str = s.get("stopAddressFull") or s.get("stopAddress")

    record = StudentRecord(
        student_id=student_id,
        unique_id=str(data.get("uniqueId", "")),
        first_name=str(data.get("firstName", "")),
        last_name=str(data.get("lastName", "")),
        location_name=data.get("locationName"),
        active_vehicle=active_bus,
        tenant_id=tenant_id,
        home_lat=h_lat,
        home_lon=h_lon,
        home_address=h_addr_str,
        school_lat=sch_lat,
        school_lon=sch_lon,
        stop_lat=st_lat,
        stop_lon=st_lon,
        stop_address=st_addr_str,
        updated_at=datetime.now(timezone.utc),
    )
    await session.merge(record)
    await session.commit()
    return record


DEFAULT_STATIC_LOCATIONS = [
    {
        "type": "school",
        "title": "Concord Road Elementary",
        "subtitle": "School Destination",
        "address": "2 Concord Rd, Ardsley, NY 10502",
        "latitude": 41.01875,
        "longitude": -73.84119,
    },
    {
        "type": "home",
        "title": "Home Address",
        "subtitle": "Student Home",
        "address": "327 Ashford Ave, Dobbs Ferry, NY 10522",
        "latitude": 41.01542,
        "longitude": -73.85293,
    },
    {
        "type": "stop",
        "title": "Bus Stop",
        "subtitle": "Pickup & Dropoff Location",
        "address": "331 Ashford Ave, Dobbs Ferry, NY 10522",
        "latitude": 41.01436,
        "longitude": -73.85389,
    },
]


async def get_static_locations(session: AsyncSession) -> list:
    stmt = select(StudentRecord).limit(1)
    result = await session.execute(stmt)
    student = result.scalar_one_or_none()

    if not student:
        return DEFAULT_STATIC_LOCATIONS

    locations = []

    # School
    locations.append(
        {
            "type": "school",
            "title": student.location_name or "Concord Road Elementary",
            "subtitle": "School Destination",
            "address": "2 Concord Rd, Ardsley, NY 10502",
            "latitude": student.school_lat or 41.01875,
            "longitude": student.school_lon or -73.84119,
        }
    )

    # Home
    locations.append(
        {
            "type": "home",
            "title": "Home Address",
            "subtitle": "Student Home",
            "address": student.home_address or "327 Ashford Ave, Dobbs Ferry, NY 10522",
            "latitude": student.home_lat or 41.01542,
            "longitude": student.home_lon or -73.85293,
        }
    )

    # Stop
    locations.append(
        {
            "type": "stop",
            "title": "Bus Stop",
            "subtitle": "Pickup & Dropoff Location",
            "address": student.stop_address or "331 Ashford Ave, Dobbs Ferry, NY 10522",
            "latitude": student.stop_lat or 41.01436,
            "longitude": student.stop_lon or -73.85389,
        }
    )

    return locations


async def get_recent_bus_locations(session: AsyncSession, limit: int = 50):
    stmt = select(BusLocation).order_by(BusLocation.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_route_dates(session: AsyncSession):
    stmt = select(func.distinct(func.substr(BusLocation.log_time, 1, 10))).where(BusLocation.log_time.is_not(None))
    result = await session.execute(stmt)
    raw_dates = result.scalars().all()
    dates = [d for d in raw_dates if d and len(d) == 10 and d[4] == "-" and d[7] == "-"]
    if not dates:
        stmt_rec = select(func.distinct(func.strftime("%Y-%m-%d", BusLocation.received_at))).where(
            BusLocation.received_at.is_not(None)
        )
        result_rec = await session.execute(stmt_rec)
        dates = [d for d in result_rec.scalars().all() if d]
    return sorted(list(set(dates)), reverse=True)


from .models import BusLocation, DailyRoute, StudentRecord
from .osrm import calculate_coords_distance_miles, match_route_osrm


async def get_route_by_date(session: AsyncSession, date_str: str):
    stmt = (
        select(BusLocation)
        .where(
            (func.substr(BusLocation.log_time, 1, 10) == date_str)
            | (func.strftime("%Y-%m-%d", BusLocation.received_at) == date_str)
        )
        .order_by(BusLocation.id.asc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_or_create_daily_route(session: AsyncSession, date_str: str):
    raw_records = await get_route_by_date(session, date_str)
    if not raw_records:
        return {"date": date_str, "vector_coords": [], "distance_miles": 0.0, "locations": []}

    stmt = select(DailyRoute).where(DailyRoute.date == date_str)
    res = await session.execute(stmt)
    cached_route = res.scalar_one_or_none()

    if cached_route:
        try:
            vector_coords = json.loads(cached_route.route_geojson)
            return {
                "date": date_str,
                "vector_coords": vector_coords,
                "distance_miles": cached_route.distance_miles,
                "locations": raw_records,
            }
        except Exception:
            pass

    raw_coords = [(r.longitude, r.latitude) for r in raw_records if r.latitude and r.longitude]
    matched = await match_route_osrm(raw_coords)
    vector_coords = [list(pt) for pt in matched]
    distance_miles = calculate_coords_distance_miles(vector_coords)

    new_route = DailyRoute(
        date=date_str,
        route_geojson=json.dumps(vector_coords),
        distance_miles=distance_miles,
        point_count=len(vector_coords),
    )
    await session.merge(new_route)
    await session.commit()

    return {
        "date": date_str,
        "vector_coords": vector_coords,
        "distance_miles": distance_miles,
        "locations": raw_records,
    }
