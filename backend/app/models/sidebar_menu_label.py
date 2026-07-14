from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SidebarMenuLabel(Base):
    __tablename__ = "sidebar_menu_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_key: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    menu_name: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
