from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.attachment import AttachmentEntityType
from app.models.user import User
from app.schemas.attachment import AttachmentRead
from app.services.attachment_service import (
    AttachmentNotFoundError,
    AttachmentValidationError,
    can_preview_attachment,
    create_attachment,
    delete_attachment,
    ensure_attachment_access,
    get_attachment,
    list_attachments,
    resolve_attachment_path,
)


router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("", response_model=List[AttachmentRead])
def read_attachments(
    entity_type: Optional[AttachmentEntityType] = Query(default=None),
    entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[AttachmentRead]:
    if entity_type is None and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="첨부파일 접근 권한이 없습니다.",
        )
    if entity_type is not None:
        ensure_attachment_access(current_user, entity_type)
    try:
        return list_attachments(db, entity_type=entity_type, entity_id=entity_id)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="첨부파일 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("/upload", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    request: Request,
    entity_type: AttachmentEntityType = Form(...),
    entity_id: int = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentRead:
    ensure_attachment_access(current_user, entity_type)
    try:
        return await create_attachment(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            upload_file=file,
            description=description,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="첨부파일을 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    try:
        attachment = get_attachment(db, attachment_id)
        ensure_attachment_access(current_user, attachment.entity_type)
        file_path = resolve_attachment_path(attachment)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="첨부파일 원본을 찾을 수 없습니다.",
            )
        return FileResponse(
            str(file_path),
            media_type=attachment.mime_type or "application/octet-stream",
            filename=attachment.original_filename,
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다.") from exc
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{attachment_id}/preview")
def preview_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    try:
        attachment = get_attachment(db, attachment_id)
        ensure_attachment_access(current_user, attachment.entity_type)
        if not can_preview_attachment(attachment):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="미리보기는 이미지와 PDF만 지원합니다.",
            )
        file_path = resolve_attachment_path(attachment)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="첨부파일 원본을 찾을 수 없습니다.",
            )
        return FileResponse(
            str(file_path),
            media_type=attachment.mime_type or "application/octet-stream",
            filename=attachment.original_filename,
            headers={"Content-Disposition": 'inline; filename="{}"'.format(attachment.original_filename.replace('"', ""))},
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다.") from exc
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{attachment_id}", response_model=AttachmentRead)
def delete_existing_attachment(
    request: Request,
    attachment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttachmentRead:
    try:
        attachment = get_attachment(db, attachment_id)
        ensure_attachment_access(current_user, attachment.entity_type)
        return delete_attachment(
            db,
            attachment_id,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except AttachmentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="첨부파일을 찾을 수 없습니다.") from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="첨부파일을 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc
