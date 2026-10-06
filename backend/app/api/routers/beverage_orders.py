from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.private_file_response import private_file_response
from app.services.private_image_path import resolve_private_image_path
from app.schemas.beverage_order_record import (
    BeverageOrderAmountOcrResponse,
    BeverageOrderRecordRead,
    BeverageOrderSummary,
)
from app.services.beverage_order_ocr_service import analyze_beverage_order_amount
from app.services.beverage_order_service import (
    BeverageOrderImageError,
    BeverageOrderRecordNotFoundError,
    create_beverage_order_record,
    delete_beverage_order_record,
    get_beverage_order_record,
    get_beverage_order_records,
    get_beverage_order_summary,
    BEVERAGE_UPLOAD_SUBDIR,
    read_beverage_image_file,
    save_beverage_image_file,
    update_beverage_order_record,
)


router = APIRouter(prefix="/beverage-orders", tags=["beverage-orders"])


@router.get("/{order_id}/image")
def read_beverage_order_image(
    request: Request,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    try:
        record = get_beverage_order_record(db, order_id)
    except BeverageOrderRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.") from exc
    if not record.image_path:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    try:
        path = resolve_private_image_path(record.image_path, BEVERAGE_UPLOAD_SUBDIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.") from exc
    return private_file_response(path, request=request, user_id=current_user.id,
                                 file_id=str(order_id), file_kind="beverage_order_image",
                                 media_type="image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else
                                 "image/" + path.suffix.lower().lstrip("."), inline=True)


@router.get("", response_model=List[BeverageOrderRecordRead])
def list_beverage_order_records(
    order_month: Optional[str] = Query(default=None),
    order_type: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[BeverageOrderRecordRead]:
    try:
        return get_beverage_order_records(
            db,
            order_month=order_month,
            order_type=order_type,
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


@router.post("/ocr/analyze-amount", response_model=BeverageOrderAmountOcrResponse)
async def analyze_beverage_order_amount_image(
    file: UploadFile = File(...),
) -> BeverageOrderAmountOcrResponse:
    content_type = (file.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 분석할 수 있습니다.",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일을 읽을 수 없습니다.",
        )
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일은 10MB 이하만 분석할 수 있습니다.",
        )

    return analyze_beverage_order_amount(image_bytes)


@router.post("/{order_id}/ocr/analyze-amount", response_model=BeverageOrderAmountOcrResponse)
def analyze_existing_beverage_order_amount_image(
    order_id: int,
    db: Session = Depends(get_db),
) -> BeverageOrderAmountOcrResponse:
    try:
        record = get_beverage_order_record(db, order_id)
        if not record.image_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="분석할 이미지가 없습니다.",
            )
        return analyze_beverage_order_amount(read_beverage_image_file(record.image_path))
    except BeverageOrderRecordNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Beverage order record not found.",
        ) from exc
    except BeverageOrderImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading beverage order image.",
        ) from exc


@router.post("", response_model=BeverageOrderRecordRead, status_code=status.HTTP_201_CREATED)
async def create_new_beverage_order_record(
    request: Request,
    order_type: str = Form(default="beverage"),
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
            order_type=normalize_order_type(order_type),
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
    order_type: str = Form(default="beverage"),
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
            order_type=normalize_order_type(order_type),
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


def normalize_order_type(value: Optional[str]) -> str:
    normalized_value = (value or "beverage").strip() or "beverage"
    if normalized_value not in {"beverage", "supplies"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_type must be beverage or supplies.",
        )
    return normalized_value
