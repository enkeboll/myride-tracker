import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from lib.models import Base
from lib.db import save_bus_location, save_student, get_recent_bus_locations, get_route_dates, get_route_by_date, get_or_create_daily_route

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
    raw_payload = "{\"type\":1,\"target\":\"NewLocation\"}"

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

@pytest.mark.asyncio
async def test_get_route_dates_and_by_date(in_memory_db: AsyncSession, ws_location_payload):
    location_data = ws_location_payload["arguments"][0]
    raw_payload = "{\"type\":1,\"target\":\"NewLocation\"}"

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
    raw_payload = "{\"type\":1,\"target\":\"NewLocation\"}"
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
