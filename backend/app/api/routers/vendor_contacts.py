from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
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
    payload: VendorContactCreate,
    db: Session = Depends(get_db),
) -> VendorContactRead:
    try:
        return create_vendor_contact(db, payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업체연락처를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{contact_id}", response_model=VendorContactRead)
def update_existing_vendor_contact(
    contact_id: int,
    payload: VendorContactUpdate,
    db: Session = Depends(get_db),
) -> VendorContactRead:
    try:
        return update_vendor_contact(db, contact_id, payload)
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
    contact_id: int,
    db: Session = Depends(get_db),
) -> VendorContactRead:
    try:
        return delete_vendor_contact(db, contact_id)
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
