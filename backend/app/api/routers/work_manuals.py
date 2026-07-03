from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.work_manual import (
    WorkManualCreate,
    WorkManualDeleteRequest,
    WorkManualRead,
    WorkManualUpdate,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.work_manual_service import (
    WorkManualNotFoundError,
    create_work_manual,
    delete_work_manual,
    get_work_manual,
    list_work_manuals,
    update_work_manual,
)


router = APIRouter(prefix="/work-manuals", tags=["work-manuals"])


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


@router.get("", response_model=List[WorkManualRead])
def read_work_manuals(db: Session = Depends(get_db)) -> List[WorkManualRead]:
    try:
        return list_work_manuals(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/{manual_id}", response_model=WorkManualRead)
def read_work_manual(manual_id: int, db: Session = Depends(get_db)) -> WorkManualRead:
    try:
        return get_work_manual(db, manual_id, increment_view_count=True)
    except WorkManualNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업무설명서를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=WorkManualRead, status_code=status.HTTP_201_CREATED)
def create_new_work_manual(
    payload: WorkManualCreate,
    db: Session = Depends(get_db),
) -> WorkManualRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return create_work_manual(db, payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{manual_id}", response_model=WorkManualRead)
def update_existing_work_manual(
    manual_id: int,
    payload: WorkManualUpdate,
    db: Session = Depends(get_db),
) -> WorkManualRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return update_work_manual(db, manual_id, payload)
    except WorkManualNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업무설명서를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 수정하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.delete("/{manual_id}", response_model=WorkManualRead)
def delete_existing_work_manual(
    manual_id: int,
    payload: WorkManualDeleteRequest,
    db: Session = Depends(get_db),
) -> WorkManualRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        return delete_work_manual(db, manual_id)
    except WorkManualNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업무설명서를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc
