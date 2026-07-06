from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


VENDOR_CONTACT_CATEGORIES = {"전산", "시설", "소모품", "렌탈", "보험", "기타"}


class VendorContactBase(BaseModel):
    category: str = Field(default="기타", max_length=40)
    company_name: str = Field(..., max_length=200)
    task_name: Optional[str] = Field(default=None, max_length=200)
    manager_name: Optional[str] = Field(default=None, max_length=100)
    phone: Optional[str] = Field(default=None, max_length=100)
    email: Optional[str] = Field(default=None, max_length=200)
    memo: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized_value = (value or "").strip() or "기타"
        if normalized_value not in VENDOR_CONTACT_CATEGORIES:
            raise ValueError("category is invalid.")
        return normalized_value

    @field_validator("company_name")
    @classmethod
    def normalize_company_name(cls, value: str) -> str:
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise ValueError("company_name is required.")
        return normalized_value

    @field_validator("task_name", "manager_name", "phone", "email", "memo")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None


class VendorContactCreate(VendorContactBase):
    pass


class VendorContactUpdate(VendorContactBase):
    pass


class VendorContactRead(VendorContactBase):
    id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
