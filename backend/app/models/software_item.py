from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SoftwareLicenseType(str, Enum):
    PERPETUAL = "영구"
    SUBSCRIPTION = "구독"
    DISCONTINUED = "사용중지"


class SoftwareItem(Base):
    __tablename__ = "software_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    owner_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    license_type: Mapped[SoftwareLicenseType] = mapped_column(
        SqlEnum(
            SoftwareLicenseType,
            name="software_license_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=SoftwareLicenseType.PERPETUAL,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expire_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    license_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
