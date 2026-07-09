from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import hash_password, require_admin
from app.db.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserAdminRead,
    UserCreate,
    UserDeleteResponse,
    UserPasswordReset,
    UserUpdate,
)


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=List[UserAdminRead])
def list_users(db: Session = Depends(get_db)) -> List[UserAdminRead]:
    return list(db.scalars(select(User).order_by(User.id.asc())).all())


@router.post("", response_model=UserAdminRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User.id).where(User.username == payload.username)) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 아이디입니다.",
        )
    user = User(
        username=payload.username,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        menu_permissions=payload.menu_permissions,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 아이디입니다.",
        ) from exc
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserAdminRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> User:
    user = _get_user_or_404(db, user_id)
    if user.id == current_admin.id and (not payload.is_active or payload.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 로그인한 관리자 계정의 권한 또는 활성 상태는 변경할 수 없습니다.",
        )
    if (
        user.role == "admin"
        and user.is_active
        and (payload.role != "admin" or not payload.is_active)
    ):
        _ensure_another_active_admin(db, user.id)
    user.name = payload.name
    user.role = payload.role
    user.is_active = payload.is_active
    user.menu_permissions = payload.menu_permissions
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=UserAdminRead)
def reset_user_password(
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
) -> User:
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", response_model=UserDeleteResponse)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> UserDeleteResponse:
    user = _get_user_or_404(db, user_id)
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 로그인한 관리자 계정은 삭제할 수 없습니다.",
        )
    if user.role == "admin" and user.is_active:
        _ensure_another_active_admin(db, user.id)
    deleted_user = UserDeleteResponse(
        id=user.id,
        username=user.username,
        message="사용자 계정을 완전히 삭제했습니다.",
    )
    db.delete(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="연관 데이터가 있어 사용자를 삭제할 수 없습니다.",
        ) from exc
    return deleted_user


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def _ensure_another_active_admin(db: Session, excluded_user_id: int) -> None:
    remaining_admin_count = db.scalar(
        select(func.count(User.id)).where(
            User.role == "admin",
            User.is_active.is_(True),
            User.id != excluded_user_id,
        )
    )
    if not remaining_admin_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="마지막 남은 관리자 계정은 삭제하거나 권한을 변경할 수 없습니다.",
        )
