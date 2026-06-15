from datetime import date, datetime
from decimal import Decimal
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.asset import AssetStatus


class AssetBase(BaseModel):
    category_id: int
    department_id: int | None = None
    department_name: str | None = Field(default=None, max_length=100)
    name: str
    model_name: str | None = None
    serial_number: str | None = Field(default=None, max_length=100)
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    user_name: str | None = None
    status: AssetStatus = AssetStatus.UNUSED
    note: str | None = None

    @field_validator("department_name")
    @classmethod
    def normalize_department_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("serial_number")
    @classmethod
    def normalize_serial_number(cls, value: str | None) -> str | None:
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
    category_id: int | None = None
    department_id: int | None = None
    department_name: str | None = Field(default=None, max_length=100)
    name: str | None = None
    model_name: str | None = None
    serial_number: str | None = Field(default=None, max_length=100)
    purchase_date: date | None = None
    purchase_price: Decimal | None = None
    user_name: str | None = None
    status: AssetStatus | None = None
    note: str | None = None

    @field_validator("department_name")
    @classmethod
    def normalize_department_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized_value = value.strip()
        return normalized_value or None

    @field_validator("serial_number")
    @classmethod
    def normalize_serial_number(cls, value: str | None) -> str | None:
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
    deleted_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AssetImportData(BaseModel):
    name: str | None = None
    category_name: str | None = None
    department_name: str | None = None
    status: AssetStatus | str | None = None
    serial_number: str | None = None
    note: str | None = None
    purchase_date: date | None = None
    model_name: str | None = None


class AssetImportPreviewRow(BaseModel):
    row_number: int
    is_valid: bool
    data: AssetImportData | None = None
    errors: list[str] = Field(default_factory=list)


class AssetImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    rows: list[AssetImportPreviewRow]


class AssetImportCommitRequest(BaseModel):
    rows: list[AssetImportPreviewRow]


class AssetImportCommitResponse(BaseModel):
    created_count: int
    skipped_count: int
    errors: list[AssetImportPreviewRow] = Field(default_factory=list)
