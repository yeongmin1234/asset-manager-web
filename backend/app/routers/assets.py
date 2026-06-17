from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.asset import AssetStatus
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.asset import AssetImportCommitRequest, AssetImportCommitResponse
from app.schemas.asset import AssetImportPreviewResponse
from app.schemas.history import AssetHistoryRead
from app.services.asset_service import (
    AssetConflictError,
    AssetNotFoundError,
    AssetValidationError,
    build_asset_import_template,
    build_assets_excel,
    commit_assets_import,
    create_asset,
    dispose_asset,
    get_asset,
    get_assets,
    preview_assets_import,
    soft_delete_asset,
    update_asset,
)
from app.services.history_service import get_asset_history


router = APIRouter(prefix="/assets", tags=["assets"])


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


@router.get("/{asset_id}", response_model=AssetRead)
def read_asset(asset_id: int, db: Session = Depends(get_db)) -> AssetRead:
    try:
        return get_asset(db, asset_id)
    except AssetNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found.",
        ) from exc
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
) -> AssetRead:
    try:
        return create_asset(
            db,
            asset_create,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
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


@router.put("/{asset_id}", response_model=AssetRead)
def update_existing_asset(
    request: Request,
    asset_id: int,
    asset_update: AssetUpdate,
    db: Session = Depends(get_db),
) -> AssetRead:
    try:
        return update_asset(
            db,
            asset_id,
            asset_update,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
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


@router.patch("/{asset_id}/dispose", response_model=AssetRead)
def dispose_existing_asset(
    request: Request,
    asset_id: int,
    db: Session = Depends(get_db),
) -> AssetRead:
    try:
        return dispose_asset(
            db,
            asset_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
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
) -> AssetRead:
    try:
        return soft_delete_asset(
            db,
            asset_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
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
