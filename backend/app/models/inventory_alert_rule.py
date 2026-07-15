from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryAlertRule(Base):
    __tablename__ = "inventory_alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    item_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    threshold_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 10), nullable=True)
    threshold_change_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 10), nullable=True)
    threshold_change_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    comparison_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true", index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, server_default="warning", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
