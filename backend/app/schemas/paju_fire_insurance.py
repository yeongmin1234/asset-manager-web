from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PajuFireInsuranceContractBase(BaseModel):
    location_group: Optional[str] = Field(default=None, max_length=50)
    warehouse_name: Optional[str] = Field(default=None, max_length=100)
    insurer_name: Optional[str] = Field(default=None, max_length=100)
    contractor: Optional[str] = Field(default=None, max_length=100)
    building_coverage: Optional[str] = Field(default=None, max_length=100)
    inventory_coverage: Optional[str] = Field(default=None, max_length=100)
    facility_coverage: Optional[str] = Field(default=None, max_length=100)
    liability_coverage: Optional[str] = Field(default=None, max_length=150)
    monthly_premium: Optional[int] = Field(default=None, ge=0)
    annual_premium: Optional[int] = Field(default=None, ge=0)
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    note: Optional[str] = None

    @field_validator(
        "location_group",
        "warehouse_name",
        "insurer_name",
        "contractor",
        "building_coverage",
        "inventory_coverage",
        "facility_coverage",
        "liability_coverage",
        "note",
    )
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None


class PajuFireInsuranceContractCreate(PajuFireInsuranceContractBase):
    pass


class PajuFireInsuranceContractUpdate(PajuFireInsuranceContractBase):
    pass


class PajuFireInsuranceContractRead(PajuFireInsuranceContractBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PajuFireInsuranceSummary(BaseModel):
    total: int = 0
    songchon: int = 0
    sinchon: int = 0
    monthly_premium_total: int = 0
    annual_premium_total: int = 0
    ending_soon: int = 0
