from datetime import datetime, timedelta
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.admin import (
    AdminPasswordRequest,
    AdminPasswordResetRequest,
    AdminPasswordResetResponse,
    AdminPasswordResponse,
    AdminStatusResponse,
    AdminVerifyRequest,
    AdminVerifyResponse,
)
from app.services.activity_log_service import record_activity_log
from app.services.admin_service import (
    AdminPasswordInvalidError,
    AdminPasswordRequiredError,
    AdminPasswordTooShortError,
    AdminResetCodeNotConfiguredError,
    is_admin_password_configured,
    reset_admin_password_with_reset_code,
    set_admin_password,
    verify_admin_reset_code,
    verify_admin_password as verify_stored_admin_password,
)


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/status", response_model=AdminStatusResponse)
def get_admin_status(db: Session = Depends(get_db)) -> AdminStatusResponse:
    return AdminStatusResponse(configured=is_admin_password_configured(db))


@router.post("/password", response_model=AdminPasswordResponse)
def update_admin_password(
    payload: AdminPasswordRequest,
    db: Session = Depends(get_db),
) -> AdminPasswordResponse:
    try:
        set_admin_password(
            db,
            payload.new_password,
            current_password=payload.current_password or None,
        )
    except AdminPasswordTooShortError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="관리자 비밀번호는 6자 이상이어야 합니다.",
        ) from exc
    except AdminPasswordRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호를 입력해주세요.",
        ) from exc
    except AdminPasswordInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="현재 비밀번호가 올바르지 않습니다.",
        ) from exc

    return AdminPasswordResponse(ok=True, configured=True)


@router.post("/password/reset", response_model=AdminPasswordResetResponse)
def reset_admin_password(
    payload: AdminPasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> AdminPasswordResetResponse:
    try:
        if payload.new_password != payload.confirm_password:
            raise AdminPasswordInvalidError()
        if not verify_admin_reset_code(payload.reset_code):
            raise AdminPasswordInvalidError()
        reset_admin_password_with_reset_code(db, payload.new_password)
    except AdminResetCodeNotConfiguredError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="관리자 비밀번호 초기화 코드가 설정되지 않았습니다.",
        ) from exc
    except (AdminPasswordTooShortError, AdminPasswordInvalidError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="초기화 코드 또는 입력값을 확인해 주세요.",
        ) from exc

    record_activity_log(
        db,
        menu_name="설정",
        action_type="admin-password-reset",
        target_type="admin",
        target_id=None,
        target_name="관리자 비밀번호",
        actor_ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        summary="관리자 비밀번호 웹 초기화",
        before_data=None,
        after_data=None,
    )
    db.commit()
    return AdminPasswordResetResponse(
        ok=True,
        message="관리자 비밀번호가 초기화되었습니다. 새 비밀번호로 다시 인증해 주세요.",
    )


@router.post("/verify", response_model=AdminVerifyResponse)
def verify_admin_password(
    payload: AdminVerifyRequest,
    db: Session = Depends(get_db),
) -> AdminVerifyResponse:
    if not is_admin_password_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )

    if not verify_stored_admin_password(db, payload.password):
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


def _get_auth_minutes() -> int:
    try:
        return max(1, int(settings.admin_auth_minutes))
    except (TypeError, ValueError):
        return 60
