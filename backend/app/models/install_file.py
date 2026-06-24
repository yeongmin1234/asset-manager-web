from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InstallFile(Base):
    __tablename__ = "install_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="기타", index=True)
    os_type: Mapped[str] = mapped_column(String(50), nullable=False, default="전체", index=True)
    version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    install_guide: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    caution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    install_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    download_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
