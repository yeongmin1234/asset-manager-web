from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict


class ActivityLogRead(BaseModel):
    id: int
    menu_name: str
    action_type: str
    target_type: str
    target_id: Optional[int] = None
    target_name: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_name: Optional[str] = None
    user_agent: Optional[str] = None
    summary: Optional[str] = None
    before_data: Optional[Dict[str, object]] = None
    after_data: Optional[Dict[str, object]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
