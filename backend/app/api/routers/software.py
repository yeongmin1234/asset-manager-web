from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.software_item import SoftwareLicenseType
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
    payload: SoftwareItemCreate,
    db: Session = Depends(get_db),
) -> SoftwareItemRead:
    try:
        return create_software_item(db, payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating software item.",
        ) from exc


@router.put("/{software_id}", response_model=SoftwareItemRead)
def update_existing_software_item(
    software_id: int,
    payload: SoftwareItemUpdate,
    db: Session = Depends(get_db),
) -> SoftwareItemRead:
    try:
        return update_software_item(db, software_id, payload)
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
    software_id: int,
    db: Session = Depends(get_db),
) -> SoftwareItemRead:
    try:
        return delete_software_item(db, software_id)
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
