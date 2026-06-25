from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ScmStatusResponse(BaseModel):
    server_name: str
    server_reachable: bool
    uptime_text: Optional[str] = None
    uptime_display: Optional[str] = None
    server_uptime_text: Optional[str] = None
    server_uptime_display: Optional[str] = None
    mariadb_active_since: Optional[str] = None
    mariadb_uptime_text: Optional[str] = None
    mariadb_uptime_display: Optional[str] = None
    mariadb_uptime_days: Optional[int] = None
    mariadb_status: str = "unknown"
    mariadb_active: bool = False
    mariadb_message: str
    db_port_reachable: bool = False
    db_port_message: str
    mariadb_restart_enabled: bool = False
    checked_at: datetime
    message: str
    status: str


class ScmMariaDbRestartDryRunRequest(BaseModel):
    admin_password: str
    reason: str
    confirm_text: str


class ScmMariaDbRestartDryRunResponse(BaseModel):
    ok: bool
    message: str
    dry_run: bool


class ScmMariaDbRestartRequest(BaseModel):
    admin_password: str
    reason: str
    confirm_text: str


class ScmMariaDbRestartResponse(BaseModel):
    ok: bool
    message: str
    before_status: str
    after_status: str
    db_port_reachable: bool
    checked_at: datetime
