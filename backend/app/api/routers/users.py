from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.auth import hash_password, require_admin
from app.db.database import get_db
from app.models.user import User
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
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
def create_user(request: Request, payload: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)) -> User:
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
    record_audit_log(db, request, current_admin, action_type="create", menu_key="user_management", menu_name="사용자 관리", target_type="user", target_id=user.id, target_name="사용자 {}".format(user.username), action_summary="사용자 계정을 생성했습니다.", after_data=audit_snapshot(user, ("username", "name", "role", "is_active", "menu_permissions")))
    return user


@router.put("/{user_id}", response_model=UserAdminRead)
def update_user(
    request: Request,
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> User:
    user = _get_user_or_404(db, user_id)
    previous_role = user.role
    previous_active = user.is_active
    previous_permissions = set(user.menu_permissions or [])
    before = audit_snapshot(user, ("name", "role", "is_active", "menu_permissions"))
    if user.id == current_admin.id and (not payload.is_active or payload.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 로그인한 관리자 계정의 권한 또는 활성 상태는 변경할 수 없습니다.",
        )
    if user.role == "admin" and payload.role != "admin":
        _ensure_another_admin(db, user.id)
    if (
        user.role == "admin"
        and user.is_active
        and not payload.is_active
    ):
        _ensure_another_active_admin(db, user.id)
    user.name = payload.name
    user.role = payload.role
    user.is_active = payload.is_active
    if payload.menu_permissions is not None:
        user.menu_permissions = payload.menu_permissions
    db.commit()
    db.refresh(user)
    action_type = "update"
    target_type = "user"
    summary = "사용자 정보를 수정했습니다."
    if previous_permissions != set(user.menu_permissions or []):
        action_type, target_type, summary = "permission_change", "user_permission", "사용자 메뉴 권한을 변경했습니다."
    elif previous_active != user.is_active:
        action_type = "activate" if user.is_active else "deactivate"
        summary = "사용자 계정을 활성화했습니다." if user.is_active else "사용자 계정을 비활성화했습니다."
    elif previous_role != user.role:
        summary = "사용자 역할을 변경했습니다."
    before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(user, ("name", "role", "is_active", "menu_permissions")))
    record_audit_log(db, request, current_admin, action_type=action_type, menu_key="user_management", menu_name="사용자 관리", target_type=target_type, target_id=user.id, target_name="사용자 {}".format(user.username), action_summary=summary, before_data=before_changed, after_data=after_changed, changed_fields=changed)
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
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> UserDeleteResponse:
    target_user = _get_user_or_404(db, user_id)
    deleted_id = target_user.id
    deleted_username = target_user.username
    before = audit_snapshot(target_user, ("username", "name", "role", "is_active", "menu_permissions"))
    if target_user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 로그인 중인 계정은 삭제할 수 없습니다.",
        )
    if target_user.role == "admin":
        _ensure_another_admin(
            db,
            target_user.id,
            "마지막 관리자 계정은 삭제할 수 없습니다.",
        )
    db.delete(target_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="연관 데이터가 있어 사용자를 삭제할 수 없습니다.",
        ) from exc
    if db.scalar(select(User.id).where(User.id == deleted_id)) is not None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 삭제 결과를 확인할 수 없습니다.",
        )
    record_audit_log(db, request, current_admin, action_type="delete", menu_key="user_management", menu_name="사용자 관리", target_type="user", target_id=deleted_id, target_name="사용자 {}".format(deleted_username), action_summary="사용자 계정을 삭제했습니다.", before_data=before)
    return UserDeleteResponse(
        id=deleted_id,
        username=deleted_username,
        message="사용자 계정을 완전히 삭제했습니다.",
    )


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def _ensure_another_active_admin(
    db: Session,
    excluded_user_id: int,
    detail: str = "마지막 남은 관리자 계정은 삭제하거나 권한을 변경할 수 없습니다.",
) -> None:
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
            detail=detail,
        )


def _ensure_another_admin(
    db: Session,
    excluded_user_id: int,
    detail: str = "마지막 남은 관리자 계정은 삭제하거나 권한을 변경할 수 없습니다.",
) -> None:
    remaining_admin_count = db.scalar(
        select(func.count(User.id)).where(
            User.role == "admin",
            User.id != excluded_user_id,
        )
    )
    if not remaining_admin_count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
