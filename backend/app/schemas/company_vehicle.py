from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.company_vehicle import VehicleOwnershipType


class CompanyVehicleBase(BaseModel):
    company_name: Optional[str] = Field(default=None, max_length=100)
    vehicle_number: str = Field(..., max_length=50)
    vehicle_name: str = Field(..., max_length=100)
    driver_name: Optional[str] = Field(default=None, max_length=100)
    ownership_type: VehicleOwnershipType = VehicleOwnershipType.COMPANY
    insurance_company: Optional[str] = Field(default=None, max_length=100)
    insurance_type: Optional[str] = Field(default=None, max_length=100)
    insurance_start_date: Optional[date] = None
    insurance_end_date: Optional[date] = None
    lease_company: Optional[str] = Field(default=None, max_length=100)
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    monthly_lease_amount: Optional[int] = Field(default=None, ge=0)
    lease_payment_day: Optional[str] = Field(default=None, max_length=50)
    tax_note: Optional[str] = None

    @field_validator("vehicle_number", "vehicle_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("required vehicle field is empty.")
        return normalized_value

    @field_validator(
        "company_name",
        "driver_name",
        "insurance_company",
        "insurance_type",
        "lease_company",
        "lease_payment_day",
        "tax_note",
    )
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None


class CompanyVehicleCreate(CompanyVehicleBase):
    pass


class CompanyVehicleUpdate(CompanyVehicleBase):
    pass


class CompanyVehicleRead(CompanyVehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompanyVehicleSummary(BaseModel):
    total_vehicles: int = 0
    company_owned_count: int = 0
    lease_count: int = 0
    expiring_soon_count: int = 0
