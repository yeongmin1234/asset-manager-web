from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.beverage_order_record import BeverageOrderRecordRead, BeverageOrderSummary
from app.services.beverage_order_service import (
    BeverageOrderImageError,
    BeverageOrderRecordNotFoundError,
    create_beverage_order_record,
    delete_beverage_order_record,
    get_beverage_order_record,
    get_beverage_order_records,
    get_beverage_order_summary,
    save_beverage_image_file,
    update_beverage_order_record,
)


router = APIRouter(prefix="/beverage-orders", tags=["beverage-orders"])


@router.get("", response_model=List[BeverageOrderRecordRead])
def list_beverage_order_records(
    order_month: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[BeverageOrderRecordRead]:
    try:
        return get_beverage_order_records(
            db,
            order_month=order_month,
            keyword=keyword,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading beverage order records.",
        ) from exc


@router.get("/summary", response_model=BeverageOrderSummary)
def read_beverage_order_summary(
    db: Session = Depends(get_db),
) -> BeverageOrderSummary:
    try:
        return get_beverage_order_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading beverage order summary.",
        ) from exc


@router.post("", response_model=BeverageOrderRecordRead, status_code=status.HTTP_201_CREATED)
async def create_new_beverage_order_record(
    request: Request,
    memo: Optional[str] = Form(default=None),
    total_amount: Optional[str] = Form(default=None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> BeverageOrderRecordRead:
    try:
        image_path, original_name = save_beverage_image_file(
            original_filename=image.filename,
            content=await image.read(),
        )
        return create_beverage_order_record(
            db,
            image_path=image_path,
            image_original_name=original_name,
            memo=memo,
            total_amount=parse_total_amount(total_amount),
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except BeverageOrderImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating beverage order record.",
        ) from exc


@router.get("/{order_id}", response_model=BeverageOrderRecordRead)
def read_beverage_order_record(
    order_id: int,
    db: Session = Depends(get_db),
) -> BeverageOrderRecordRead:
    try:
        return get_beverage_order_record(db, order_id)
    except BeverageOrderRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage order record not found.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading beverage order record.",
        ) from exc


@router.put("/{order_id}", response_model=BeverageOrderRecordRead)
async def update_existing_beverage_order_record(
    request: Request,
    order_id: int,
    memo: Optional[str] = Form(default=None),
    total_amount: Optional[str] = Form(default=None),
    image: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
) -> BeverageOrderRecordRead:
    image_path = None
    original_name = None
    try:
        if image is not None and image.filename:
            image_path, original_name = save_beverage_image_file(
                original_filename=image.filename,
                content=await image.read(),
            )
        return update_beverage_order_record(
            db,
            order_id,
            memo=memo,
            total_amount=parse_total_amount(total_amount),
            image_path=image_path,
            image_original_name=original_name,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except BeverageOrderRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage order record not found.",
        ) from exc
    except BeverageOrderImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating beverage order record.",
        ) from exc


@router.delete("/{order_id}", response_model=BeverageOrderRecordRead)
def delete_existing_beverage_order_record(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
) -> BeverageOrderRecordRead:
    try:
        return delete_beverage_order_record(
            db,
            order_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except BeverageOrderRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage order record not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting beverage order record.",
        ) from exc


def parse_total_amount(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        amount = int(value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_amount must be a number.",
        ) from exc
    if amount < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="total_amount must be greater than or equal to 0.",
        )
    return amount
