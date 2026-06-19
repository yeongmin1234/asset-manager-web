from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, HTTPException, status

from app.core.config import settings
from app.schemas.admin import AdminVerifyRequest, AdminVerifyResponse


router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/verify", response_model=AdminVerifyResponse)
def verify_admin_password(payload: AdminVerifyRequest) -> AdminVerifyResponse:
    if not _is_admin_password_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )

    if not _is_valid_admin_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="비밀번호가 올바르지 않습니다.",
        )

    expires_at = datetime.utcnow() + timedelta(minutes=_get_auth_minutes())
    return AdminVerifyResponse(
        ok=True,
        token=secrets.token_urlsafe(32),
        expires_at=expires_at,
    )


def _is_admin_password_configured() -> bool:
    return bool(settings.admin_password or settings.admin_password_hash)


def _is_valid_admin_password(password: str) -> bool:
    if settings.admin_password_hash:
        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return secrets.compare_digest(password_hash, settings.admin_password_hash)

    if settings.admin_password:
        return secrets.compare_digest(password, settings.admin_password)

    return False


def _get_auth_minutes() -> int:
    try:
        return max(1, int(settings.admin_auth_minutes))
    except (TypeError, ValueError):
        return 60
