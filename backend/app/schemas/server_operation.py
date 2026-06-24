from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScmStatusResponse(BaseModel):
    server_name: str
    reachable: bool
    uptime_text: Optional[str] = None
    checked_at: datetime
    message: str
    status: str


class ScmRebootDryRunRequest(BaseModel):
    admin_password: str
    reason: str
    confirm_text: str


class ScmRebootDryRunResponse(BaseModel):
    ok: bool
    message: str
    dry_run: bool
