from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MenuVisibilitySetting(Base):
    __tablename__ = "menu_visibility_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
