from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.dashboard_notice import DashboardNoticeType


class DashboardNoticeBase(BaseModel):
    notice_type: DashboardNoticeType = DashboardNoticeType.NOTICE
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=5000)
    is_pinned: bool = False

    @field_validator("title", "content")
    @classmethod
    def normalize_required_text(cls, value: str, info):
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise ValueError("{} is required.".format(info.field_name))
        return normalized_value


class DashboardNoticeCreate(DashboardNoticeBase):
    admin_password: str = Field(..., min_length=1)


class DashboardNoticeUpdate(DashboardNoticeBase):
    admin_password: str = Field(..., min_length=1)


class DashboardNoticeDeleteRequest(BaseModel):
    admin_password: str = Field(..., min_length=1)


class DashboardNoticeRead(DashboardNoticeBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
