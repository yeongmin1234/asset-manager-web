from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BeverageOrderRecordBase(BaseModel):
    order_date: Optional[date] = None
    order_month: Optional[str] = Field(default=None, max_length=7)
    vendor: Optional[str] = Field(default=None, max_length=100)
    title: str = Field(..., min_length=1, max_length=200)
    items_summary: Optional[str] = None
    total_amount: Optional[int] = Field(default=None, ge=0)
    quantity_summary: Optional[str] = None
    requester: Optional[str] = Field(default=None, max_length=100)
    payment_method: Optional[str] = Field(default=None, max_length=100)
    order_url: Optional[str] = None
    image_path: Optional[str] = None
    image_original_name: Optional[str] = Field(default=None, max_length=255)
    memo: Optional[str] = None

    @field_validator(
        "order_month",
        "vendor",
        "items_summary",
        "quantity_summary",
        "requester",
        "payment_method",
        "order_url",
        "image_path",
        "image_original_name",
        "memo",
    )
    @classmethod
    def normalize_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("title is required")
        return normalized_value


class BeverageOrderRecordCreate(BeverageOrderRecordBase):
    pass


class BeverageOrderRecordUpdate(BeverageOrderRecordBase):
    pass


class BeverageOrderRecordRead(BeverageOrderRecordBase):
    id: int
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BeverageOrderSummary(BaseModel):
    total: int = 0
    this_month: int = 0
    total_amount_total: int = 0
    this_month_amount: int = 0
