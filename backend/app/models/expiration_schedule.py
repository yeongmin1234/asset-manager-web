from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExpirationScheduleCategory(str, Enum):
    VEHICLE_INSURANCE = "vehicle_insurance"
    VEHICLE_INSPECTION = "vehicle_inspection"
    FIRE_INSURANCE = "fire_insurance"
    CONTRACT = "contract"
    RENTAL = "rental"
    SOFTWARE_LICENSE = "software_license"
    WARRANTY = "warranty"
    SERVER_MAINTENANCE = "server_maintenance"
    NAS_MAINTENANCE = "nas_maintenance"
    OTHER = "other"


class ExpirationScheduleStatus(str, Enum):
    OVERDUE = "overdue"
    WITHIN_7_DAYS = "within_7_days"
    WITHIN_30_DAYS = "within_30_days"
    NORMAL = "normal"
    COMPLETED = "completed"


class ExpirationSchedule(Base):
    __tablename__ = "expiration_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[ExpirationScheduleCategory] = mapped_column(
        SqlEnum(
            ExpirationScheduleCategory,
            name="expiration_schedule_category",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    target_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notification_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="30")
    status: Mapped[ExpirationScheduleStatus] = mapped_column(
        SqlEnum(
            ExpirationScheduleStatus,
            name="expiration_schedule_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        server_default=ExpirationScheduleStatus.NORMAL.value,
        index=True,
    )
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
