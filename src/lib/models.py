from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BusLocation(Base):
    __tablename__ = "bus_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_unique_id: Mapped[str] = mapped_column(String(50), index=True)
    asset_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    log_time: Mapped[str | None] = mapped_column(String(50), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    vendor_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visible_run_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_payload: Mapped[str] = mapped_column(Text)

    __table_args__ = (Index("idx_asset_log_time_unique", "asset_unique_id", "log_time", unique=True),)


class StudentRecord(Base):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    location_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    active_vehicle: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    school_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    school_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    stop_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_address: Mapped[str | None] = mapped_column(String(200), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DailyRoute(Base):
    __tablename__ = "daily_routes"

    date: Mapped[str] = mapped_column(String(20), primary_key=True)
    route_geojson: Mapped[str] = mapped_column(Text)
    distance_miles: Mapped[float] = mapped_column(Float, default=0.0)
    point_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
