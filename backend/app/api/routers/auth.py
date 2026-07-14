from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.schemas.login_access_log import LogoutResponse
from app.services.login_access_log_service import record_access_log


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    user = db.scalar(select(User).where(User.username == username))
    failure_reason = None
    if user is None:
        failure_reason = "존재하지 않는 사용자"
    elif not user.is_active:
        failure_reason = "비활성 계정"
    elif not verify_password(payload.password, user.password_hash):
        failure_reason = "비밀번호 불일치"
    if failure_reason:
        record_access_log(
            db, request,
            user_id=user.id if user else None,
            username=username,
            user_name=user.name if user else None,
            event_type="login",
            login_result="failure",
            failure_reason=failure_reason,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )
    access_token = create_access_token(user)
    user_read = UserRead.model_validate(user)
    record_access_log(
        db, request,
        user_id=user.id,
        username=user.username,
        user_name=user.name,
        event_type="login",
        login_result="success",
    )
    return LoginResponse(access_token=access_token, user=user_read)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LogoutResponse:
    record_access_log(
        db, request,
        user_id=user.id,
        username=user.username,
        user_name=user.name,
        event_type="logout",
        login_result="success",
    )
    return LogoutResponse(ok=True)
