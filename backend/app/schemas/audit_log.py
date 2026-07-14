from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    id: int
    user_id: int
    username: str
    user_name: str
    action_type: str
    menu_key: str
    menu_name: str
    target_type: str
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    action_summary: str
    ip_address: Optional[str] = None
    access_type: str
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    occurred_at: datetime
    changed_fields: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogPage(BaseModel):
    items: List[AuditLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int
    menu_options: List[dict] = Field(default_factory=list)
    target_type_options: List[str] = Field(default_factory=list)


class AuditLogDetail(AuditLogRead):
    before_data: Optional[dict] = None
    after_data: Optional[dict] = None
