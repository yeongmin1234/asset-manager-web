from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrderManagementReady(BaseModel):
    status: Literal["ready"] = "ready"
    message: str = "발주관리 기능 준비 중"


class OrderDashboardResponse(OrderManagementReady):
    today_count: int = 0
    success_count: int = 0
    mapping_required_count: int = 0
    error_count: int = 0


class OrderListResponse(OrderManagementReady):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class OrderChannelCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9_]+$")
    description: str = Field(default="", max_length=1000)
    is_active: bool = True
    is_default: bool = False

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("채널명을 입력하세요.")
        return value


class OrderChannelUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    description: str = Field(max_length=1000)
    is_active: bool
    is_default: bool

    @field_validator("name")
    @classmethod
    def nonempty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("채널명을 입력하세요.")
        return value


class OrderChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str
    is_active: bool
    is_default: bool
    processing_supported: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
