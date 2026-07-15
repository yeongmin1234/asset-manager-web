from datetime import datetime, time
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventorySchedule(Base):
    __tablename__ = "inventory_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    run_time: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, server_default="Asia/Seoul")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false", index=True)
    target_mode: Mapped[str] = mapped_column(String(32), nullable=False, server_default="selected_items")
    target_item_codes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list, server_default="[]")
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )
