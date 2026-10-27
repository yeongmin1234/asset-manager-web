"""Short-lived, single-process SCM handoff. No asset database writes."""
from hashlib import sha256
from collections import deque
from secrets import compare_digest, token_urlsafe
from threading import Lock
from time import monotonic

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.auth import get_current_user
from app.core.config import settings
from app.models.user import User

router = APIRouter(prefix="/auth/scm-handoff", tags=["auth"])
_codes: dict[str, tuple[int, float, str]] = {}
_lock = Lock()
_audience = "new-scm"
_ttl_seconds = 45
_max_pending = 1000
_exchange_attempts: deque[float] = deque()
_max_exchanges_per_minute = 120


class ExchangeRequest(BaseModel):
    code: str = Field(min_length=32, max_length=256)
    audience: str = Field(min_length=1, max_length=40)


def _deny() -> HTTPException:
    return HTTPException(status_code=401, detail="유효하지 않은 인증 인계입니다.")


@router.post("/issue")
def issue(user: User = Depends(get_current_user)):
    if user.role != "admin" and "scm_app" not in (user.menu_permissions or []):
        raise HTTPException(status_code=403, detail="SCM 진입 권한이 없습니다.")
    if not settings.scm_handoff_key or len(settings.scm_handoff_key) < 32:
        raise HTTPException(status_code=503, detail="SCM 인증 인계가 설정되지 않았습니다.")
    code = token_urlsafe(48)
    now = monotonic()
    with _lock:
        for digest, (_, expires, _) in list(_codes.items()):
            if expires <= now:
                del _codes[digest]
        if len(_codes) >= _max_pending:
            raise HTTPException(status_code=503, detail="잠시 후 다시 시도해주세요.")
        _codes[sha256(code.encode()).hexdigest()] = (user.id, now + _ttl_seconds, _audience)
    return {"code": code, "expires_in": _ttl_seconds}


@router.post("/exchange")
def exchange(payload: ExchangeRequest, x_scm_handoff_key: str | None = Header(default=None)):
    now = monotonic()
    with _lock:
        while _exchange_attempts and _exchange_attempts[0] <= now - 60:
            _exchange_attempts.popleft()
        if len(_exchange_attempts) >= _max_exchanges_per_minute:
            raise HTTPException(status_code=429, detail="잠시 후 다시 시도해주세요.")
        _exchange_attempts.append(now)
    key = settings.scm_handoff_key
    if not key or len(key) < 32 or not x_scm_handoff_key or not compare_digest(key, x_scm_handoff_key):
        raise _deny()
    if payload.audience != _audience:
        raise _deny()
    with _lock:
        entry = _codes.pop(sha256(payload.code.encode()).hexdigest(), None)
    if entry is None or entry[1] <= monotonic() or entry[2] != payload.audience:
        raise _deny()
    return {"issuer": "asset-manager", "subject": str(entry[0]), "audience": _audience}
