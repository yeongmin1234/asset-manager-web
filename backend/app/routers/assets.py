from datetime import date
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.asset import Asset, AssetStatus
from app.models.user import User
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
from app.schemas.asset import AssetCreate, AssetOcrAnalysisResponse, AssetRead, AssetUpdate
from app.schemas.asset import AssetImportCommitRequest, AssetImportCommitResponse
from app.schemas.asset import AssetImportPreviewResponse
from app.schemas.history import AssetHistoryRead
from app.services.asset_service import (
    AssetConflictError,
    AssetImageError,
    AssetNotFoundError,
    AssetValidationError,
    build_asset_import_template,
    build_assets_excel,
    commit_assets_import,
    create_asset,
    delete_asset_image_file,
    dispose_asset,
    get_asset,
    ASSET_UPLOAD_SUBDIR,
    get_assets,
    preview_assets_import,
    save_asset_image_file,
    soft_delete_asset,
    update_asset,
)
from app.services.attachment_service import AttachmentValidationError
from app.services.asset_ocr_service import analyze_asset_image
from app.services.private_file_response import private_file_response
from app.services.private_image_path import resolve_private_image_path
from app.services.history_service import get_asset_history


router = APIRouter(prefix="/assets", tags=["assets"])
logger = logging.getLogger(__name__)


@router.get("/{asset_id}/spec-image")
def read_asset_spec_image(
    request: Request,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    try:
        asset = get_asset(db, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.") from exc
    if not asset.spec_image_path:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    try:
        path = resolve_private_image_path(asset.spec_image_path, ASSET_UPLOAD_SUBDIR)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.") from exc
    return private_file_response(path, request=request, user_id=current_user.id,
                                 file_id=str(asset_id), file_kind="asset_spec_image",
                                 media_type="image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else
                                 "image/" + path.suffix.lower().lstrip("."), inline=True)


@router.get("", response_model=List[AssetRead])
def list_assets(
    status_filter: Optional[AssetStatus] = Query(default=None, alias="status"),
    category_id: Optional[int] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    location_group: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
) -> List[AssetRead]:
    try:
        return get_assets(
            db,
            status=status_filter,
            category_id=category_id,
            department_id=department_id,
            department_name=department_name,
            location_group=location_group,
            keyword=keyword,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading assets.",
        ) from exc


@router.get("/export/excel")
def export_assets_excel(
    status_filter: Optional[AssetStatus] = Query(default=None, alias="status"),
    category_id: Optional[int] = None,
    department_id: Optional[int] = None,
    department_name: Optional[str] = None,
    location_group: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        assets = get_assets(
            db,
            status=status_filter,
            category_id=category_id,
            department_id=department_id,
            department_name=department_name,
            location_group=location_group,
            keyword=keyword,
        )
        excel_file = build_assets_excel(assets)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while exporting assets.",
        ) from exc

    filename = f"asset_list_{date.today().isoformat()}.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/import/template")
def download_asset_import_template() -> StreamingResponse:
    template_file = build_asset_import_template()
    headers = {
        "Content-Disposition": 'attachment; filename="asset_import_template.xlsx"',
    }
    return StreamingResponse(
        template_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/import/preview", response_model=AssetImportPreviewResponse)
async def preview_asset_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> AssetImportPreviewResponse:
    try:
        file_bytes = await file.read()
        return preview_assets_import(db, file_bytes)
    except AssetValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while previewing asset import.",
        ) from exc


@router.post("/import/commit", response_model=AssetImportCommitResponse)
def commit_asset_import(
    payload: AssetImportCommitRequest,
    db: Session = Depends(get_db),
) -> AssetImportCommitResponse:
    try:
        return commit_assets_import(db, payload.rows)
    except AssetValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while importing assets.",
        ) from exc


@router.post("/ocr/analyze", response_model=AssetOcrAnalysisResponse)
async def analyze_asset_spec_image(
    file: UploadFile = File(...),
) -> AssetOcrAnalysisResponse:
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

    try:
        return analyze_asset_image(image_bytes)
    except Exception as exc:
        logger.exception("Asset OCR analysis failed unexpectedly.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "이미지 분석을 완료하지 못했습니다. "
                "라벨이 선명하게 보이도록 다시 촬영하거나 다시 업로드해 주세요."
            ),
        ) from exc


@router.get("/{asset_id}", response_model=AssetRead)
def read_asset(asset_id: int, db: Session = Depends(get_db)) -> AssetRead:
    try:
        return get_asset(db, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading asset.",
        ) from exc


@router.get("/{asset_id}/history", response_model=List[AssetHistoryRead])
def list_asset_history(
    asset_id: int,
    db: Session = Depends(get_db),
) -> List[AssetHistoryRead]:
    try:
        get_asset(db, asset_id)
        return get_asset_history(db, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading asset history.",
        ) from exc


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_new_asset(
    request: Request,
    asset_create: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    try:
        result = create_asset(
            db,
            asset_create,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 등록했습니다.", after_data=audit_snapshot(result, ("name", "model_name", "serial_number", "department_name", "user_name", "status")))
        return result
    except AssetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="serial_number already exists.",
        ) from exc
    except AssetValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating asset.",
        ) from exc


@router.post("/with-image", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
async def create_new_asset_with_image(
    request: Request,
    category_id: str = Form(...),
    name: str = Form(...),
    status_value: str = Form(..., alias="status"),
    department_id: Optional[str] = Form(default=None),
    department_name: Optional[str] = Form(default=None),
    location_group: Optional[str] = Form(default=None),
    location_detail: Optional[str] = Form(default=None),
    model_name: Optional[str] = Form(default=None),
    serial_number: Optional[str] = Form(default=None),
    purchase_date: Optional[str] = Form(default=None),
    purchase_price: Optional[str] = Form(default=None),
    user_name: Optional[str] = Form(default=None),
    note: Optional[str] = Form(default=None),
    spec_image: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    spec_image_path = None
    try:
        if spec_image is not None and spec_image.filename:
            spec_image_path, _original_name = save_asset_image_file(
                original_filename=spec_image.filename,
                content=await spec_image.read(),
            )
        payload = build_asset_create_from_form(
            category_id=category_id,
            department_id=department_id,
            department_name=department_name,
            location_group=location_group,
            location_detail=location_detail,
            name=name,
            model_name=model_name,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_price=purchase_price,
            user_name=user_name,
            status_value=status_value,
            note=note,
            spec_image_path=spec_image_path,
        )
        result = create_asset(
            db,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 등록했습니다.", after_data=audit_snapshot(result, ("name", "model_name", "serial_number", "department_name", "user_name", "status")))
        return result
    except AssetImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AssetConflictError as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="serial_number already exists.",
        ) from exc
    except (AssetValidationError, ValueError) as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating asset.",
        ) from exc


@router.put("/{asset_id}", response_model=AssetRead)
def update_existing_asset(
    request: Request,
    asset_id: int,
    asset_update: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    try:
        fields = ("category_id", "department_id", "department_name", "location_group", "location_detail", "name", "model_name", "serial_number", "purchase_date", "purchase_price", "user_name", "status", "note")
        before = audit_snapshot(db.get(Asset, asset_id), fields)
        result = update_asset(
            db,
            asset_id,
            asset_update,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except AssetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="serial_number already exists.",
        ) from exc
    except AssetValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating asset.",
        ) from exc


@router.put("/{asset_id}/with-image", response_model=AssetRead)
async def update_existing_asset_with_image(
    request: Request,
    asset_id: int,
    category_id: Optional[str] = Form(default=None),
    department_id: Optional[str] = Form(default=None),
    department_name: Optional[str] = Form(default=None),
    location_group: Optional[str] = Form(default=None),
    location_detail: Optional[str] = Form(default=None),
    name: Optional[str] = Form(default=None),
    model_name: Optional[str] = Form(default=None),
    serial_number: Optional[str] = Form(default=None),
    purchase_date: Optional[str] = Form(default=None),
    purchase_price: Optional[str] = Form(default=None),
    user_name: Optional[str] = Form(default=None),
    status_value: Optional[str] = Form(default=None, alias="status"),
    note: Optional[str] = Form(default=None),
    delete_spec_image: Optional[str] = Form(default=None),
    spec_image: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    spec_image_path = None
    try:
        fields = ("category_id", "department_id", "department_name", "location_group", "location_detail", "name", "model_name", "serial_number", "purchase_date", "purchase_price", "user_name", "status", "note", "spec_image_path")
        before = audit_snapshot(db.get(Asset, asset_id), fields)
        update_fields = build_asset_update_fields_from_form(
            category_id=category_id,
            department_id=department_id,
            department_name=department_name,
            location_group=location_group,
            location_detail=location_detail,
            name=name,
            model_name=model_name,
            serial_number=serial_number,
            purchase_date=purchase_date,
            purchase_price=purchase_price,
            user_name=user_name,
            status_value=status_value,
            note=note,
        )
        if spec_image is not None and spec_image.filename:
            spec_image_path, _original_name = save_asset_image_file(
                original_filename=spec_image.filename,
                content=await spec_image.read(),
            )
            update_fields["spec_image_path"] = spec_image_path
        elif is_truthy_form_value(delete_spec_image):
            update_fields["spec_image_path"] = None

        result = update_asset(
            db,
            asset_id,
            AssetUpdate(**update_fields),
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except AssetImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AssetNotFoundError as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except AssetConflictError as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="serial_number already exists.",
        ) from exc
    except (AssetValidationError, ValueError) as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except SQLAlchemyError as exc:
        if spec_image_path:
            delete_asset_image_file(spec_image_path)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating asset.",
        ) from exc


@router.patch("/{asset_id}/dispose", response_model=AssetRead)
def dispose_existing_asset(
    request: Request,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    try:
        before = audit_snapshot(db.get(Asset, asset_id), ("status",))
        result = dispose_asset(
            db,
            asset_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, ("status",)))
        record_audit_log(db, request, current_user, action_type="update", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 폐기 처리했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while disposing asset.",
        ) from exc


@router.delete("/{asset_id}", response_model=AssetRead)
def delete_existing_asset(
    request: Request,
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetRead:
    try:
        before = audit_snapshot(db.get(Asset, asset_id), ("name", "model_name", "serial_number", "department_name", "user_name", "status"))
        result = soft_delete_asset(
            db,
            asset_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="delete", menu_key="assets", menu_name="자산 관리", target_type="asset", target_id=result.id, target_name=result.name, action_summary="자산을 삭제했습니다.", before_data=before)
        return result
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting asset.",
        ) from exc


def build_asset_create_from_form(
    *,
    category_id: str,
    department_id: Optional[str],
    department_name: Optional[str],
    location_group: Optional[str],
    location_detail: Optional[str],
    name: str,
    model_name: Optional[str],
    serial_number: Optional[str],
    purchase_date: Optional[str],
    purchase_price: Optional[str],
    user_name: Optional[str],
    status_value: str,
    note: Optional[str],
    spec_image_path: Optional[str],
) -> AssetCreate:
    return AssetCreate(
        category_id=parse_required_int(category_id, "category_id"),
        department_id=parse_optional_int(department_id, "department_id"),
        department_name=empty_to_none(department_name),
        location_group=empty_to_none(location_group),
        location_detail=empty_to_none(location_detail),
        name=name,
        model_name=empty_to_none(model_name),
        serial_number=empty_to_none(serial_number),
        purchase_date=empty_to_none(purchase_date),
        purchase_price=empty_to_none(purchase_price),
        user_name=empty_to_none(user_name),
        status=AssetStatus(status_value),
        note=empty_to_none(note),
        spec_image_path=spec_image_path,
    )


def build_asset_update_fields_from_form(
    *,
    category_id: Optional[str],
    department_id: Optional[str],
    department_name: Optional[str],
    location_group: Optional[str],
    location_detail: Optional[str],
    name: Optional[str],
    model_name: Optional[str],
    serial_number: Optional[str],
    purchase_date: Optional[str],
    purchase_price: Optional[str],
    user_name: Optional[str],
    status_value: Optional[str],
    note: Optional[str],
) -> Dict[str, object]:
    fields: Dict[str, object] = {}
    if category_id is not None:
        fields["category_id"] = parse_required_int(category_id, "category_id")
    if department_id is not None:
        fields["department_id"] = parse_optional_int(department_id, "department_id")
    for field_name, value in (
        ("department_name", department_name),
        ("location_group", location_group),
        ("location_detail", location_detail),
        ("name", name),
        ("model_name", model_name),
        ("serial_number", serial_number),
        ("purchase_date", purchase_date),
        ("purchase_price", purchase_price),
        ("user_name", user_name),
        ("note", note),
    ):
        if value is not None:
            fields[field_name] = empty_to_none(value)
    if status_value is not None:
        fields["status"] = AssetStatus(status_value)
    return fields


def empty_to_none(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized_value = value.strip()
    return normalized_value or None


def parse_required_int(value: str, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def parse_optional_int(value: Optional[str], field_name: str) -> Optional[int]:
    if value is None or value.strip() == "":
        return None
    return parse_required_int(value, field_name)


def is_truthy_form_value(value: Optional[str]) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}
