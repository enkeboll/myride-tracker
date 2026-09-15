import json
from datetime import datetime, timezone
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import settings
from .models import Base, BusLocation, StudentRecord

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

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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

    record = StudentRecord(
        student_id=student_id,
        unique_id=str(data.get("uniqueId", "")),
        first_name=str(data.get("firstName", "")),
        last_name=str(data.get("lastName", "")),
        location_name=data.get("locationName"),
        active_vehicle=active_bus,
        tenant_id=tenant_id,
        updated_at=datetime.now(timezone.utc),
    )
    await session.merge(record)
    await session.commit()
    return record

async def get_recent_bus_locations(session: AsyncSession, limit: int = 50):
    stmt = select(BusLocation).order_by(BusLocation.id.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
