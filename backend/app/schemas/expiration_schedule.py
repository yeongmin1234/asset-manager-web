from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.expiration_schedule import (
    ExpirationScheduleCategory,
    ExpirationScheduleStatus,
)


class ExpirationScheduleBase(BaseModel):
    category: ExpirationScheduleCategory
    title: str = Field(..., min_length=1, max_length=200)
    target_name: str = Field(..., min_length=1, max_length=200)
    due_date: date
    notification_days: int = Field(default=30, ge=0, le=3650)
    memo: Optional[str] = None
    source_type: Optional[str] = Field(default=None, max_length=80)
    source_id: Optional[int] = None

    @field_validator("title", "target_name", "source_type")
    @classmethod
    def strip_optional_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("필수 입력값입니다.")
        return normalized

    @field_validator("memo")
    @classmethod
    def strip_memo(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ExpirationScheduleCreate(ExpirationScheduleBase):
    pass


class ExpirationScheduleUpdate(ExpirationScheduleBase):
    is_completed: bool = False


class ExpirationScheduleCompleteRequest(BaseModel):
    is_completed: bool = True


class ExpirationScheduleRead(BaseModel):
    id: int
    category: ExpirationScheduleCategory
    title: str
    target_name: str
    due_date: date
    notification_days: int
    status: ExpirationScheduleStatus
    memo: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[int] = None
    is_completed: bool
    completed_at: Optional[datetime] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    days_left: int

    model_config = ConfigDict(from_attributes=True)


class ExpirationScheduleSummary(BaseModel):
    overdue_count: int = 0
    within_7_days_count: int = 0
    within_30_days_count: int = 0
    normal_count: int = 0
    completed_count: int = 0
    upcoming_items: List[ExpirationScheduleRead] = Field(default_factory=list)
