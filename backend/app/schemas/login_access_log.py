from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class LoginAccessLogRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    username: str
    user_name: Optional[str] = None
    event_type: str
    login_result: str
    ip_address: Optional[str] = None
    access_type: str
    user_agent: Optional[str] = None
    browser: Optional[str] = None
    operating_system: Optional[str] = None
    failure_reason: Optional[str] = None
    occurred_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginAccessLogPage(BaseModel):
    items: List[LoginAccessLogRead]
    total: int
    page: int
    page_size: int
    total_pages: int


class LogoutResponse(BaseModel):
    ok: bool = True
