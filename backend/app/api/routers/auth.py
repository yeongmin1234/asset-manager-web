from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, verify_password
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserRead


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    username = payload.username.strip()
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않습니다.",
        )
    return LoginResponse(
        access_token=create_access_token(user),
        user=UserRead.model_validate(user),
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(user)
