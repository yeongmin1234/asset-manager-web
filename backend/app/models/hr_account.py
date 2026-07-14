from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class HrAccount(Base):
    __tablename__ = "hr_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dowoffice: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    erp: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    scm: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    nas: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
