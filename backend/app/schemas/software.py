from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.software_item import SoftwareLicenseType


class SoftwareItemBase(BaseModel):
    name: str = Field(..., max_length=200)
    owner_name: Optional[str] = Field(default=None, max_length=100)
    license_type: SoftwareLicenseType = SoftwareLicenseType.PERPETUAL
    quantity: int = Field(default=1, ge=0)
    expire_date: Optional[date] = None
    note: Optional[str] = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("software name is required.")
        return normalized_value

    @field_validator("owner_name", "note")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None


class SoftwareItemCreate(SoftwareItemBase):
    pass


class SoftwareItemUpdate(SoftwareItemBase):
    pass


class SoftwareItemRead(SoftwareItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SoftwareStatsSummary(BaseModel):
    total_software: int = 0
    perpetual_count: int = 0
    subscription_count: int = 0
    discontinued_count: int = 0
