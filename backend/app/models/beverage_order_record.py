from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BeverageOrderRecord(Base):
    __tablename__ = "beverage_order_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="beverage", index=True)
    order_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    order_month: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, index=True)
    vendor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    items_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_amount: Mapped[Optional[int]] = mapped_column(Numeric(14, 0), nullable=True)
    quantity_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requester: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    order_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_original_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    memo: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    @property
    def image_url(self) -> Optional[str]:
        if not self.image_path:
            return None
        return f"/uploads/{self.image_path}"
