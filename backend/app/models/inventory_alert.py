from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventoryAlert(Base):
    __tablename__ = "inventory_alerts"
    __table_args__ = (
        Index(
            "uq_inventory_alert_open_rule_item_type", "rule_id", "item_code", "alert_type",
            unique=True,
            postgresql_where=text("status IN ('active', 'acknowledged')"),
            sqlite_where=text("status IN ('active', 'acknowledged')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    rule_id: Mapped[int] = mapped_column(ForeignKey("inventory_alert_rules.id", ondelete="RESTRICT"), nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    item_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    last_detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    snapshot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inventory_snapshots.id", ondelete="SET NULL"), nullable=True)
    previous_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 10), nullable=True)
    current_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    change_quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 10), nullable=True)
    change_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    threshold_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="active", index=True)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    partial_result: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    safe_message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
