from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MenuAccessLog(Base):
    __tablename__ = "menu_access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    menu_key: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    menu_name: Mapped[str] = mapped_column(String(100), nullable=False)
    route_path: Mapped[str] = mapped_column(String(200), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    access_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    browser: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    operating_system: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True,
    )
