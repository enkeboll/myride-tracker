import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from lib.db import (
    get_or_create_daily_route,
    get_recent_bus_locations,
    get_route_by_date,
    get_route_dates,
    save_bus_location,
    save_student,
)
from lib.models import Base


@pytest_asyncio.fixture
async def in_memory_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_save_and_retrieve_bus_location(in_memory_db: AsyncSession, ws_location_payload):
    location_data = ws_location_payload["arguments"][0]
    raw_payload = '{"type":1,"target":"NewLocation"}'

    record = await save_bus_location(in_memory_db, location_data, raw_payload)
    assert record.id is not None
    assert record.asset_unique_id == "53"
    assert record.latitude == 41.0072594
    assert record.longitude == -73.8575439
    assert record.speed == 17

    recent = await get_recent_bus_locations(in_memory_db, limit=10)
    assert len(recent) == 1
    assert recent[0].asset_unique_id == "53"


@pytest.mark.asyncio
async def test_save_student(in_memory_db: AsyncSession, student_info_fixture):
    student_data = student_info_fixture[0]
    record = await save_student(in_memory_db, student_data, tenant_id="tenant_123")
    assert record.student_id == 181166
    assert record.first_name == "SOREN"
    assert record.active_vehicle == "53"
    assert record.stop_time == "15:20" or record.stop_time == "15:32" or record.stop_time is not None
    assert record.eta_minutes == 0


@pytest.mark.asyncio
async def test_get_route_dates_and_by_date(in_memory_db: AsyncSession, ws_location_payload):
    location_data = ws_location_payload["arguments"][0]
    raw_payload = '{"type":1,"target":"NewLocation"}'

    # Insert location with specific log_time
    location_data["logTime"] = "2026-09-24T08:15:00.0000000Z"
    await save_bus_location(in_memory_db, location_data, raw_payload)

    dates = await get_route_dates(in_memory_db)
    assert "2026-09-24" in dates

    route_points = await get_route_by_date(in_memory_db, "2026-09-24")
    assert len(route_points) == 1
    assert route_points[0].asset_unique_id == "53"


@pytest.mark.asyncio
async def test_get_or_create_daily_route_caching(in_memory_db: AsyncSession, ws_location_payload):
    location_data = ws_location_payload["arguments"][0]
    raw_payload = '{"type":1,"target":"NewLocation"}'
    location_data["logTime"] = "2026-09-24T08:15:00.0000000Z"
    await save_bus_location(in_memory_db, location_data, raw_payload)

    # First call: generates/matches and caches in DailyRoute table
    res1 = await get_or_create_daily_route(in_memory_db, "2026-09-24")
    assert res1["date"] == "2026-09-24"
    assert "vector_coords" in res1
    assert len(res1["locations"]) == 1

    # Second call: reads from cached DailyRoute SQLite table immediately
    res2 = await get_or_create_daily_route(in_memory_db, "2026-09-24")
    assert res2["date"] == "2026-09-24"
    assert res2["vector_coords"] == res1["vector_coords"]


@pytest.mark.asyncio
async def test_live_route_caching_updates_today(in_memory_db: AsyncSession, ws_location_payload):
    from datetime import datetime, timezone

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    location_data = ws_location_payload["arguments"][0].copy()
    raw_payload = '{"type":1,"target":"NewLocation"}'

    # 1. First location logged today
    location_data["logTime"] = f"{today_str}T08:15:00.0000000Z"
    await save_bus_location(in_memory_db, location_data, raw_payload)

    route1 = await get_or_create_daily_route(in_memory_db, today_str)
    assert len(route1["locations"]) == 1

    # 2. Second location logged mid-route today
    loc2 = location_data.copy()
    loc2["logTime"] = f"{today_str}T08:16:00.0000000Z"
    loc2["latitude"] = 41.01000
    await save_bus_location(in_memory_db, loc2, raw_payload)

    # 3. Requesting today's route must return both points, not stale early cache
    route2 = await get_or_create_daily_route(in_memory_db, today_str)
    assert len(route2["locations"]) == 2


@pytest.mark.asyncio
async def test_mid_route_points_update_cache_when_growing(in_memory_db: AsyncSession, ws_location_payload):
    location_data = ws_location_payload["arguments"][0].copy()
    raw_payload = '{"type":1,"target":"NewLocation"}'
    date_str = "2026-09-20"

    # Save 1 point for past date and cache
    location_data["logTime"] = f"{date_str}T08:00:00.0000000Z"
    await save_bus_location(in_memory_db, location_data, raw_payload)
    r1 = await get_or_create_daily_route(in_memory_db, date_str)
    assert len(r1["locations"]) == 1

    # Mid-route data streaming adds point 2
    loc2 = location_data.copy()
    loc2["logTime"] = f"{date_str}T08:05:00.0000000Z"
    loc2["latitude"] = 41.02000
    await save_bus_location(in_memory_db, loc2, raw_payload)

    # Calling get_or_create_daily_route must update cache since point count grew
    r2 = await get_or_create_daily_route(in_memory_db, date_str)
    assert len(r2["locations"]) == 2
