from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InventorySnapshot(Base):
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "snapshot_group_id", "item_code", "row_type", "warehouse_code",
            name="uq_inventory_snapshot_group_item_row_warehouse",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_group_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    schedule_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("inventory_schedules.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    row_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    item_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    item_name: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, index=True)
    unit: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    warehouse_code: Mapped[str] = mapped_column(String(20), nullable=False, server_default="")
    warehouse_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    total_quantity: Mapped[Decimal] = mapped_column(Numeric(30, 10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
