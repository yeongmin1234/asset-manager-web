from datetime import date, datetime
from decimal import Decimal
import re
from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import AssetStatus


class AssetBase(BaseModel):
    category_id: int
    department_id: Optional[int] = None
    department_name: Optional[str] = Field(default=None, max_length=100)
    location_group: Optional[str] = Field(default=None, max_length=50)
    location_detail: Optional[str] = Field(default=None, max_length=150)
    name: str
    model_name: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, max_length=100)
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    user_name: Optional[str] = None
    status: AssetStatus = AssetStatus.UNUSED
    note: Optional[str] = None
    spec_image_path: Optional[str] = None

    @field_validator("department_name", "location_group", "location_detail")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("serial_number")
    @classmethod
    def normalize_serial_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized_value = value.strip().upper()
        if not normalized_value:
            return None
        if re.fullmatch(r"[A-Z0-9]+", normalized_value) is None:
            raise ValueError("serial_number must contain only A-Z and 0-9.")
        return normalized_value


class AssetCreate(AssetBase):
    status: AssetStatus


class AssetUpdate(BaseModel):
    category_id: Optional[int] = None
    department_id: Optional[int] = None
    department_name: Optional[str] = Field(default=None, max_length=100)
    location_group: Optional[str] = Field(default=None, max_length=50)
    location_detail: Optional[str] = Field(default=None, max_length=150)
    name: Optional[str] = None
    model_name: Optional[str] = None
    serial_number: Optional[str] = Field(default=None, max_length=100)
    purchase_date: Optional[date] = None
    purchase_price: Optional[Decimal] = None
    user_name: Optional[str] = None
    status: Optional[AssetStatus] = None
    note: Optional[str] = None
    spec_image_path: Optional[str] = None

    @field_validator("department_name", "location_group", "location_detail")
    @classmethod
    def normalize_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("serial_number")
    @classmethod
    def normalize_serial_number(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized_value = value.strip().upper()
        if not normalized_value:
            return None
        if re.fullmatch(r"[A-Z0-9]+", normalized_value) is None:
            raise ValueError("serial_number must contain only A-Z and 0-9.")
        return normalized_value


class AssetRead(AssetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    spec_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AssetImportData(BaseModel):
    name: Optional[str] = None
    category_name: Optional[str] = None
    department_name: Optional[str] = None
    status: Optional[Union[AssetStatus, str]] = None
    serial_number: Optional[str] = None
    note: Optional[str] = None
    purchase_date: Optional[date] = None
    model_name: Optional[str] = None


class AssetImportPreviewRow(BaseModel):
    row_number: int
    is_valid: bool
    data: Optional[AssetImportData] = None
    errors: List[str] = Field(default_factory=list)


class AssetImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    rows: List[AssetImportPreviewRow]


class AssetImportCommitRequest(BaseModel):
    rows: List[AssetImportPreviewRow]


class AssetImportCommitResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: List[AssetImportPreviewRow] = Field(default_factory=list)


class AssetOcrAnalysisResponse(BaseModel):
    product_name: Optional[str] = None
    manufacturer: Optional[str] = None
    model_name: Optional[str] = None
    product_number: Optional[str] = None
    serial_number: Optional[str] = None
    source: Optional[str] = None
    message: str
    raw_text: Optional[str] = None
