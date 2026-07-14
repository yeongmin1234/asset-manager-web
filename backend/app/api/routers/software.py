from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
from app.models.software_item import SoftwareItem, SoftwareLicenseType
from app.schemas.software import (
    SoftwareItemCreate,
    SoftwareItemRead,
    SoftwareItemUpdate,
    SoftwareStatsSummary,
)
from app.services.software_service import (
    SoftwareItemNotFoundError,
    create_software_item,
    delete_software_item,
    get_software_items,
    get_software_stats_summary,
    update_software_item,
)


router = APIRouter(prefix="/software", tags=["software"])


@router.get("", response_model=List[SoftwareItemRead])
def list_software_items(
    keyword: Optional[str] = None,
    license_type: Optional[SoftwareLicenseType] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[SoftwareItemRead]:
    try:
        return get_software_items(db, keyword=keyword, license_type=license_type)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading software items.",
        ) from exc


@router.post("", response_model=SoftwareItemRead, status_code=status.HTTP_201_CREATED)
def create_new_software_item(
    request: Request,
    payload: SoftwareItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoftwareItemRead:
    try:
        result = create_software_item(
            db,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="software", menu_name="SW 현황", target_type="software", target_id=result.id, target_name=result.name, action_summary="SW를 등록했습니다.", after_data=audit_snapshot(result, ("name", "owner_name", "license_type", "quantity", "expire_date", "note")))
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating software item.",
        ) from exc


@router.put("/{software_id}", response_model=SoftwareItemRead)
def update_existing_software_item(
    request: Request,
    software_id: int,
    payload: SoftwareItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoftwareItemRead:
    try:
        fields = ("name", "owner_name", "license_type", "quantity", "price_amount", "expire_date", "note")
        before = audit_snapshot(db.get(SoftwareItem, software_id), fields)
        result = update_software_item(
            db,
            software_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="software", menu_name="SW 현황", target_type="software", target_id=result.id, target_name=result.name, action_summary="SW를 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except SoftwareItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Software item not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating software item.",
        ) from exc


@router.delete("/{software_id}", response_model=SoftwareItemRead)
def delete_existing_software_item(
    request: Request,
    software_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SoftwareItemRead:
    try:
        before = audit_snapshot(db.get(SoftwareItem, software_id), ("name", "owner_name", "license_type", "quantity", "expire_date", "note"))
        result = delete_software_item(
            db,
            software_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="delete", menu_key="software", menu_name="SW 현황", target_type="software", target_id=result.id, target_name=result.name, action_summary="SW를 삭제했습니다.", before_data=before)
        return result
    except SoftwareItemNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Software item not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting software item.",
        ) from exc


@router.get("/summary", response_model=SoftwareStatsSummary)
def read_software_stats_summary(
    db: Session = Depends(get_db),
) -> SoftwareStatsSummary:
    try:
        return get_software_stats_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading software stats.",
        ) from exc
