from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class VehicleInsuranceHistoryBase(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    insurance_type: Optional[str] = Field(default=None, max_length=100)
    driver_name: Optional[str] = Field(default=None, max_length=100)
    amount: Optional[int] = Field(default=None, ge=0)
    payment_method: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None

    @field_validator("insurance_type", "driver_name", "payment_method", "note")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None


class VehicleInsuranceHistoryCreate(VehicleInsuranceHistoryBase):
    pass


class VehicleInsuranceHistoryUpdate(VehicleInsuranceHistoryBase):
    pass


class VehicleInsuranceHistoryRead(VehicleInsuranceHistoryBase):
    id: int
    vehicle_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
