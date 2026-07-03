from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkManualBase(BaseModel):
    category: str = Field(default="일반", max_length=80)
    title: str = Field(..., max_length=200)
    content: str = Field(..., max_length=10000)
    author: str = Field(default="관리자", max_length=80)
    is_pinned: bool = False

    @field_validator("category", "title", "content", "author")
    @classmethod
    def normalize_required_text(cls, value: str, info):
        normalized_value = (value or "").strip()
        if not normalized_value:
            raise ValueError("{} is required.".format(info.field_name))
        return normalized_value


class WorkManualCreate(WorkManualBase):
    pass


class WorkManualUpdate(WorkManualBase):
    pass


class WorkManualRead(WorkManualBase):
    id: int
    is_active: bool
    view_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkManualImageUploadResponse(BaseModel):
    url: str
    filename: str
