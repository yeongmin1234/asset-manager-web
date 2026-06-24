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


class AdminPasswordResetRequest(BaseModel):
    reset_code: str
    new_password: str
    confirm_password: str


class AdminPasswordResetResponse(BaseModel):
    ok: bool
    message: str


class AdminVerifyResponse(BaseModel):
    ok: bool
    token: str
    expires_at: datetime
