from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


UserRole = Literal["admin", "user"]
ALLOWED_MENU_PERMISSIONS = {
    "dashboard",
    "drink_orders",
    "expiration_schedules",
    "work_manual",
    "vendor_contacts",
    "assets",
    "software",
    "company_cars",
    "fire_insurance",
    "access_info",
    "equipment_status",
    "statistics",
    "changelog",
    "hr_list",
    "online_home",
    "online_recall",
    "online_order",
}

LEGACY_MENU_PERMISSION_MAP = {
    "beverage-orders": "drink_orders",
    "work-manuals": "work_manual",
    "vendor-contacts": "vendor_contacts",
    "vehicles": "company_cars",
    "paju-fire-insurance": "fire_insurance",
    "stats": "statistics",
    "history": "changelog",
}


def normalize_menu_permissions(values: List[str]) -> List[str]:
    normalized_values = []
    for value in values:
        if value == "network":
            normalized_values.extend(["access_info", "equipment_status"])
        else:
            normalized_values.append(LEGACY_MENU_PERMISSION_MAP.get(value, value))
    invalid_values = [value for value in normalized_values if value not in ALLOWED_MENU_PERMISSIONS]
    if invalid_values:
        raise ValueError(f"지원하지 않는 메뉴 권한입니다: {', '.join(invalid_values)}")
    return list(dict.fromkeys(normalized_values))


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
    menu_permissions: Optional[List[str]] = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("이름은 필수입니다.")
        return normalized

    @field_validator("menu_permissions")
    @classmethod
    def validate_menu_permissions(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
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
