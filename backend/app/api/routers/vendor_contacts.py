from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.vendor_contact import VendorContact
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
from app.schemas.vendor_contact import (
    VendorContactCreate,
    VendorContactRead,
    VendorContactUpdate,
)
from app.services.vendor_contact_service import (
    VendorContactNotFoundError,
    create_vendor_contact,
    delete_vendor_contact,
    list_vendor_contacts,
    update_vendor_contact,
)
from app.services.attachment_service import AttachmentValidationError


router = APIRouter(prefix="/vendor-contacts", tags=["vendor-contacts"])


@router.get("", response_model=List[VendorContactRead])
def read_vendor_contacts(
    category: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[VendorContactRead]:
    try:
        return list_vendor_contacts(db, category=category, keyword=keyword)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업체연락처 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=VendorContactRead, status_code=status.HTTP_201_CREATED)
def create_new_vendor_contact(
    request: Request,
    payload: VendorContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VendorContactRead:
    try:
        result = create_vendor_contact(db, payload)
        record_audit_log(db, request, current_user, action_type="create", menu_key="vendor_contacts", menu_name="업체연락처", target_type="vendor_contact", target_id=result.id, target_name=result.company_name, action_summary="업체연락처를 등록했습니다.", after_data=audit_snapshot(result, ("category", "company_name", "task_name", "manager_name", "phone", "email")))
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업체연락처를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{contact_id}", response_model=VendorContactRead)
def update_existing_vendor_contact(
    request: Request,
    contact_id: int,
    payload: VendorContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VendorContactRead:
    try:
        fields = ("category", "company_name", "task_name", "manager_name", "phone", "email", "memo", "is_favorite")
        before = audit_snapshot(db.get(VendorContact, contact_id), fields)
        result = update_vendor_contact(db, contact_id, payload)
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="vendor_contacts", menu_name="업체연락처", target_type="vendor_contact", target_id=result.id, target_name=result.company_name, action_summary="업체연락처를 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except VendorContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업체연락처를 찾을 수 없습니다.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업체연락처를 수정하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.delete("/{contact_id}", response_model=VendorContactRead)
def delete_existing_vendor_contact(
    request: Request,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VendorContactRead:
    try:
        before = audit_snapshot(db.get(VendorContact, contact_id), ("category", "company_name", "task_name", "manager_name", "phone", "email"))
        result = delete_vendor_contact(db, contact_id)
        record_audit_log(db, request, current_user, action_type="delete", menu_key="vendor_contacts", menu_name="업체연락처", target_type="vendor_contact", target_id=result.id, target_name=result.company_name, action_summary="업체연락처를 삭제했습니다.", before_data=before)
        return result
    except VendorContactNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업체연락처를 찾을 수 없습니다.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업체연락처를 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc
