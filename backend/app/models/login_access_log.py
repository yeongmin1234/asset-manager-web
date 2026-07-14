from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginAccessLog(Base):
    __tablename__ = "login_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    login_result: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True,
    )
