from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AssetStatus(str, Enum):
    IN_USE = "사용중"
    UNUSED = "미사용"
    DISPOSED = "폐기"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    department_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    location_detail: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    model_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    serial_number: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    purchase_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2),
        nullable=True,
    )
    user_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[AssetStatus] = mapped_column(
        SqlEnum(
            AssetStatus,
            name="asset_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=AssetStatus.UNUSED,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spec_image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    category = relationship("Category", back_populates="assets")
    department = relationship("Department", back_populates="assets")
    history = relationship("AssetHistory", back_populates="asset")

    @property
    def spec_image_url(self) -> Optional[str]:
        if not self.spec_image_path:
            return None
        return f"/uploads/{self.spec_image_path}"
