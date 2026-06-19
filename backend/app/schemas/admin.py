from datetime import datetime

from pydantic import BaseModel


class AdminVerifyRequest(BaseModel):
    password: str


class AdminStatusResponse(BaseModel):
    configured: bool


class AdminPasswordRequest(BaseModel):
    new_password: str
    current_password: str = ""


class AdminPasswordResponse(BaseModel):
    ok: bool
    configured: bool


class AdminVerifyResponse(BaseModel):
    ok: bool
    token: str
    expires_at: datetime
