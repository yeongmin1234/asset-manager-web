from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, Enum as SqlEnum, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AttachmentEntityType(str, Enum):
    ASSET = "asset"
    VENDOR_CONTACT = "vendor_contact"
    WORK_MANUAL = "work_manual"
    COMPANY_CAR = "company_car"
    FIRE_INSURANCE = "fire_insurance"
    EXPIRATION_SCHEDULE = "expiration_schedule"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    entity_type: Mapped[AttachmentEntityType] = mapped_column(
        SqlEnum(
            AttachmentEntityType,
            name="attachment_entity_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
