from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PajuFireInsuranceContract(Base):
    __tablename__ = "paju_fire_insurance_contracts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    location_group: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    warehouse_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    insurer_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    contractor: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    building_coverage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    inventory_coverage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    facility_coverage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    liability_coverage: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    monthly_premium: Mapped[Optional[int]] = mapped_column(Numeric(14, 0), nullable=True)
    annual_premium: Mapped[Optional[int]] = mapped_column(Numeric(14, 0), nullable=True)
    contract_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    contract_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
