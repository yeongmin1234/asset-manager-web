from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import DateTime, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemActivityLog(Base):
    __tablename__ = "system_activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    menu_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    target_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    actor_ip: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    actor_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    before_data: Mapped[Optional[Dict[str, object]]] = mapped_column(JSON, nullable=True)
    after_data: Mapped[Optional[Dict[str, object]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
