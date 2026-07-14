from datetime import date, datetime, timedelta
import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

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
from app.schemas.login_access_log import LoginAccessLogPage
from app.schemas.audit_log import AuditLogPage
from app.schemas.menu_access_log import MenuAccessLogPage
from app.services.login_access_log_service import get_access_logs
from app.services.audit_log_service import get_audit_logs
from app.services.menu_access_log_service import get_menu_access_logs
from app.services.admin_service import (
    AdminPasswordInvalidError,
    AdminPasswordRequiredError,
    AdminPasswordTooShortError,
    AdminResetCodeNotConfiguredError,
    create_admin_auth_token,
    is_admin_password_configured,
    reset_admin_password_with_reset_code,
    set_admin_password,
    verify_admin_reset_code,
    verify_admin_password as verify_stored_admin_password,
)


router = APIRouter(prefix="/admin", tags=["admin"])
logger = logging.getLogger(__name__)


@router.get("/access-logs", response_model=LoginAccessLogPage)
def list_login_access_logs(
    keyword: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    event_type: Optional[Literal["login", "logout"]] = Query(default=None),
    login_result: Optional[Literal["success", "failure"]] = Query(default=None),
    access_type: Optional[Literal["internal", "external"]] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> LoginAccessLogPage:
    try:
        return get_access_logs(
            db,
            keyword=keyword,
            username=username,
            event_type=event_type,
            login_result=login_result,
            access_type=access_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to load login access logs")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="접속기록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/menu-access-logs", response_model=MenuAccessLogPage)
def list_menu_access_logs(
    keyword: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    menu_key: Optional[str] = Query(default=None),
    access_type: Optional[Literal["internal", "external"]] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> MenuAccessLogPage:
    try:
        return get_menu_access_logs(
            db,
            keyword=keyword,
            username=username,
            menu_key=menu_key,
            access_type=access_type,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to load menu access logs")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="메뉴 접근 기록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/audit-logs", response_model=AuditLogPage)
def list_audit_logs(
    keyword: Optional[str] = Query(default=None),
    username: Optional[str] = Query(default=None),
    action_type: Optional[Literal["create", "update", "delete", "activate", "deactivate", "permission_change", "excel_import"]] = Query(default=None),
    menu_key: Optional[str] = Query(default=None),
    target_type: Optional[str] = Query(default=None),
    access_type: Optional[Literal["internal", "external"]] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> AuditLogPage:
    try:
        return get_audit_logs(
            db, keyword=keyword, username=username, action_type=action_type,
            menu_key=menu_key, target_type=target_type, access_type=access_type,
            start_date=start_date, end_date=end_date, page=page, page_size=page_size,
        )
    except SQLAlchemyError as exc:
        logger.exception("Failed to load audit logs")
        raise HTTPException(status_code=503, detail="감사로그를 불러오는 중 DB 연결에 실패했습니다.") from exc


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
        token=create_admin_auth_token(db, expires_at),
        expires_at=expires_at,
    )


def _get_auth_minutes() -> int:
    try:
        return max(1, int(settings.admin_auth_minutes))
    except (TypeError, ValueError):
        return 60
