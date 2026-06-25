from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard_notice import (
    DashboardNoticeCreate,
    DashboardNoticeDeleteRequest,
    DashboardNoticeRead,
    DashboardNoticeUpdate,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.dashboard_notice_service import (
    DashboardNoticeNotFoundError,
    create_dashboard_notice,
    delete_dashboard_notice,
    list_dashboard_notices,
    update_dashboard_notice,
)


router = APIRouter(prefix="/dashboard-notices", tags=["dashboard-notices"])


def verify_admin_guard(db: Session, admin_password: str) -> None:
    if not is_admin_password_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )
    if not verify_admin_password(db, admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 비밀번호를 확인해 주세요.",
        )


@router.get("", response_model=List[DashboardNoticeRead])
def read_dashboard_notices(db: Session = Depends(get_db)) -> List[DashboardNoticeRead]:
    try:
        return list_dashboard_notices(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="공지사항 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=DashboardNoticeRead, status_code=status.HTTP_201_CREATED)
def create_new_dashboard_notice(
    payload: DashboardNoticeCreate,
    db: Session = Depends(get_db),
) -> DashboardNoticeRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return create_dashboard_notice(db, payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="공지사항을 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{notice_id}", response_model=DashboardNoticeRead)
def update_existing_dashboard_notice(
    notice_id: int,
    payload: DashboardNoticeUpdate,
    db: Session = Depends(get_db),
) -> DashboardNoticeRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return update_dashboard_notice(db, notice_id, payload)
    except DashboardNoticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="공지사항을 수정하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.delete("/{notice_id}", response_model=DashboardNoticeRead)
def delete_existing_dashboard_notice(
    notice_id: int,
    payload: DashboardNoticeDeleteRequest,
    db: Session = Depends(get_db),
) -> DashboardNoticeRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return delete_dashboard_notice(db, notice_id)
    except DashboardNoticeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="공지사항을 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="공지사항을 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc
