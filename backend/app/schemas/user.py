from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRole = Literal["admin", "user"]
ALLOWED_MENU_PERMISSIONS = {
    "dashboard",
    "beverage-orders",
    "work-manuals",
    "vendor-contacts",
    "assets",
    "software",
    "vehicles",
    "paju-fire-insurance",
    "network",
    "stats",
    "history",
}


def normalize_menu_permissions(values: List[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value in ALLOWED_MENU_PERMISSIONS))


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=200)
    role: UserRole = "user"
    menu_permissions: List[str] = Field(default_factory=lambda: ["dashboard", "assets"])

    @field_validator("username", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("필수 입력값입니다.")
        return normalized

    @field_validator("menu_permissions")
    @classmethod
    def validate_menu_permissions(cls, values: List[str]) -> List[str]:
        return normalize_menu_permissions(values)


class UserUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole
    is_active: bool
    menu_permissions: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("이름은 필수입니다.")
        return normalized

    @field_validator("menu_permissions")
    @classmethod
    def validate_menu_permissions(cls, values: List[str]) -> List[str]:
        return normalize_menu_permissions(values)


class UserPasswordReset(BaseModel):
    password: str = Field(..., min_length=8, max_length=200)


class UserAdminRead(BaseModel):
    id: int
    username: str
    name: str
    role: UserRole
    is_active: bool
    menu_permissions: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDeleteResponse(BaseModel):
    id: int
    username: str
    message: str
