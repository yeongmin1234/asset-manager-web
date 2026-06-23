from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.network_credential import (
    NetworkCredentialCategory,
    NetworkCredentialImportance,
)


MASKED_PASSWORD = "••••••••"


class NetworkCredentialBase(BaseModel):
    category: NetworkCredentialCategory = NetworkCredentialCategory.ETC
    service_name: str = Field(..., max_length=200)
    internal_url: Optional[str] = Field(default=None, max_length=500)
    external_url: Optional[str] = Field(default=None, max_length=500)
    port: Optional[str] = Field(default=None, max_length=40)
    username: Optional[str] = Field(default=None, max_length=200)
    importance: NetworkCredentialImportance = NetworkCredentialImportance.NORMAL
    owner: Optional[str] = Field(default=None, max_length=100)
    note: Optional[str] = None
    is_active: bool = True

    @field_validator(
        "service_name",
        "internal_url",
        "external_url",
        "port",
        "username",
        "owner",
        "note",
    )
    @classmethod
    def normalize_text(cls, value: Optional[str], info):
        if value is None:
            return None
        normalized_value = value.strip()
        if info.field_name == "service_name" and not normalized_value:
            raise ValueError("service name is required.")
        return normalized_value or None

    @model_validator(mode="after")
    def validate_urls(self):
        if not self.internal_url and not self.external_url:
            raise ValueError("internal_url or external_url is required.")
        return self


class NetworkCredentialCreate(NetworkCredentialBase):
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def normalize_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value or None


class NetworkCredentialUpdate(NetworkCredentialBase):
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def normalize_update_password(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value or None


class NetworkCredentialRead(NetworkCredentialBase):
    id: int
    has_password: bool
    password_mask: str = MASKED_PASSWORD
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NetworkCredentialRevealRequest(BaseModel):
    admin_password: str = Field(..., min_length=1)


class NetworkCredentialRevealResponse(BaseModel):
    password: str
    expires_in: int = 15
    message: Optional[str] = None


class NetworkCredentialSummary(BaseModel):
    total: int = 0
    important: int = 0
    critical: int = 0
    with_password: int = 0
