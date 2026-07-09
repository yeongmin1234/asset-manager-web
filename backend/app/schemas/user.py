from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRole = Literal["admin", "user"]


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=200)
    role: UserRole = "user"

    @field_validator("username", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("필수 입력값입니다.")
        return normalized


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    is_active: bool

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("이름은 필수입니다.")
        return normalized


class UserPasswordReset(BaseModel):
    password: str = Field(..., min_length=8, max_length=200)


class UserAdminRead(BaseModel):
    id: int
    username: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
