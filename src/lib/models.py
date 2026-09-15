from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class BusLocation(Base):
    __tablename__ = "bus_locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_unique_id: Mapped[str] = mapped_column(String(50), index=True)
    asset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    log_time: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    heading: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    vendor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visible_run_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    raw_payload: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index("idx_asset_log_time", "asset_unique_id", "log_time"),
    )

class StudentRecord(Base):
    __tablename__ = "students"

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    unique_id: Mapped[str] = mapped_column(String(50))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    location_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    active_vehicle: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
