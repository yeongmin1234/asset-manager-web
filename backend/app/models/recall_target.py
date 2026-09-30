from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RecallTargetUploadBatch(Base):
    __tablename__ = "recall_target_upload_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, nullable=False)
    normal_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)


class RecallTarget(Base):
    __tablename__ = "recall_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("recall_target_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sales_channel: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    original_order_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    phone_raw: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone_normalized: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, index=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivery_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    duplicate_reason: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    duplicate_reference_id: Mapped[Optional[int]] = mapped_column(ForeignKey("recall_targets.id", ondelete="SET NULL"), nullable=True)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    review_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
