from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


MenuAccessKey = Literal[
    "dashboard", "drink_orders", "work_manual", "vendor_contacts",
    "expiration_schedules", "assets", "software", "company_cars",
    "fire_insurance", "access_info", "equipment_status", "excel_management", "statistics",
    "history", "install_files", "hr_list", "scm", "user_management",
    "settings", "excel_import",
]


class MenuAccessLogCreate(BaseModel):
    menu_key: MenuAccessKey
    menu_name: str = Field(..., min_length=1, max_length=100)
    route_path: str = Field(..., min_length=1, max_length=200)

    @field_validator("menu_name", "route_path")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class MenuAccessLogCreateResponse(BaseModel):
    ok: bool = True
    recorded: bool
    deduplicated: bool


class MenuAccessLogRead(BaseModel):
    id: int
    user_id: int
    username: str
    user_name: str
    menu_key: str
    menu_name: str
    route_path: str
    ip_address: Optional[str] = None
    access_type: str
    user_agent: Optional[str] = None
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuAccessLogPage(BaseModel):
    items: List[MenuAccessLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int
    menu_options: List[dict] = Field(default_factory=list)
