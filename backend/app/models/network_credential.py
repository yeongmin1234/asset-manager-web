from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NetworkCredentialCategory(str, Enum):
    NAS = "NAS"
    CCTV = "CCTV"
    SERVER = "서버"
    PRINTER = "프린터"
    ROUTER = "공유기"
    VPN = "VPN"
    WEB_ADMIN = "웹관리자"
    ETC = "기타"


class NetworkCredentialImportance(str, Enum):
    NORMAL = "일반"
    IMPORTANT = "중요"
    CRITICAL = "매우중요"


class NetworkCredential(Base):
    __tablename__ = "network_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    category: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=NetworkCredentialCategory.ETC.value,
        server_default=NetworkCredentialCategory.ETC.value,
        index=True,
    )
    service_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    internal_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    external_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    port: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    encrypted_password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    importance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=NetworkCredentialImportance.NORMAL.value,
        server_default=NetworkCredentialImportance.NORMAL.value,
        index=True,
    )
    owner: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        index=True,
    )
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
