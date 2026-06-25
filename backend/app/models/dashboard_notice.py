from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DashboardNoticeType(str, Enum):
    NOTICE = "공지"
    UPDATE = "업데이트"
    MAINTENANCE = "점검"
    ETC = "기타"


class DashboardNotice(Base):
    __tablename__ = "dashboard_notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    notice_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DashboardNoticeType.NOTICE.value,
        server_default=DashboardNoticeType.NOTICE.value,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        index=True,
    )
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
