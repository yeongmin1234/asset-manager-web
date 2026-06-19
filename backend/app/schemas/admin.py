from datetime import datetime

from pydantic import BaseModel


class AdminVerifyRequest(BaseModel):
    password: str


class AdminVerifyResponse(BaseModel):
    ok: bool
    token: str
    expires_at: datetime
