from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, LargeBinary, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
IN_PROGRESS = "IN_PROGRESS"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
STOPPED = "STOPPED"
SHIPPED = "SHIPPED"
ORDER_PENDING = "ORDER_PENDING"
ORDER_EXPORTED = "ORDER_EXPORTED"
ORDER_CONFIRMED = "ORDER_CONFIRMED"


class RecallApplicationUploadBatch(Base):
    __tablename__ = "recall_application_upload_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registered_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)


class RecallApplication(Base):
    __tablename__ = "recall_applications"
    __table_args__ = (
        UniqueConstraint("upload_batch_id", "source_row_number", name="uq_recall_application_batch_row"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_batch_id: Mapped[int] = mapped_column(
        ForeignKey("recall_application_upload_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    application_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    quantity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone_original: Mapped[str] = mapped_column(String(50), nullable=False)
    phone_normalized: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_agreement: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pickup_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    replacement_shipping_agreement: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    review_reason_codes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    current_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=APPLICATION_RECEIVED, server_default=APPLICATION_RECEIVED, index=True
    )
    order_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default=ORDER_PENDING, server_default=ORDER_PENDING, index=True
    )
    order_exported_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    order_batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recall_order_batches.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    duplicate_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    duplicate_reason: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    duplicate_reference_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recall_applications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    duplicate_resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duplicate_resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    duplicate_resolution: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    duplicate_registration_attempt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    duplicate_registration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_duplicate_registration_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_duplicate_registration_batch_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recall_application_upload_batches.id", ondelete="SET NULL"), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false", index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    delete_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    delete_reason_category: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)


class RecallStatusHistory(Base):
    __tablename__ = "recall_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recall_application_id: Mapped[int] = mapped_column(
        ForeignKey("recall_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_status: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    new_status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class RecallOrderBatch(Base):
    __tablename__ = "recall_order_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    file_content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)


class RecallDuplicateResolutionHistory(Base):
    __tablename__ = "recall_duplicate_resolution_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recall_application_id: Mapped[int] = mapped_column(
        ForeignKey("recall_applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
