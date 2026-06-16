from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VehicleOwnershipType(str, Enum):
    COMPANY = "회사"
    LEASE = "리스"


class CompanyVehicle(Base):
    __tablename__ = "company_vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    vehicle_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    vehicle_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    driver_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ownership_type: Mapped[VehicleOwnershipType] = mapped_column(
        SqlEnum(
            VehicleOwnershipType,
            name="vehicle_ownership_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=VehicleOwnershipType.COMPANY,
    )
    insurance_company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    insurance_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    insurance_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lease_company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lease_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    lease_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    monthly_lease_amount: Mapped[Optional[int]] = mapped_column(Numeric(14, 0), nullable=True)
    lease_payment_day: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tax_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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
