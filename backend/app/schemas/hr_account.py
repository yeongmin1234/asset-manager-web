from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HrAccountBase(BaseModel):
    department: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    dowoffice: Optional[str] = Field(default=None, max_length=200)
    erp: Optional[str] = Field(default=None, max_length=200)
    scm: Optional[str] = Field(default=None, max_length=200)
    nas: Optional[str] = Field(default=None, max_length=200)

    @field_validator("department", "name")
    @classmethod
    def normalize_required(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("필수 입력값입니다.")
        return value

    @field_validator("dowoffice", "erp", "scm", "nas")
    @classmethod
    def normalize_optional(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


class HrAccountCreate(HrAccountBase):
    pass


class HrAccountUpdate(HrAccountBase):
    pass


class HrAccountRead(HrAccountBase):
    id: int
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class HrAccountImportData(BaseModel):
    department: Optional[str] = None
    name: Optional[str] = None
    dowoffice: Optional[str] = None
    erp: Optional[str] = None
    scm: Optional[str] = None
    nas: Optional[str] = None


class HrAccountImportPreviewRow(BaseModel):
    row_number: int
    status: Literal["valid", "duplicate", "error"]
    data: HrAccountImportData
    errors: List[str] = Field(default_factory=list)


class HrAccountImportPreviewResponse(BaseModel):
    matched_columns: Dict[str, str]
    total_count: int
    valid_count: int
    duplicate_count: int
    error_count: int
    rows: List[HrAccountImportPreviewRow]


class HrAccountImportRequest(BaseModel):
    rows: List[HrAccountImportPreviewRow] = Field(..., max_length=5000)
    duplicate_policy: Literal["skip", "update"] = "skip"


class HrAccountImportResponse(BaseModel):
    created_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
