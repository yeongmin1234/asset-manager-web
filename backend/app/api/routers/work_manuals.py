from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.schemas.work_manual import (
    WorkManualCreate,
    WorkManualImageUploadResponse,
    WorkManualRead,
    WorkManualUpdate,
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
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
WORK_MANUAL_IMAGE_DIR = "work_manuals/images"


@router.get("", response_model=List[WorkManualRead])
def read_work_manuals(db: Session = Depends(get_db)) -> List[WorkManualRead]:
    try:
        return list_work_manuals(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("/images", response_model=WorkManualImageUploadResponse)
async def upload_work_manual_image(
    image: UploadFile = File(...),
) -> WorkManualImageUploadResponse:
    extension = Path(image.filename or "").suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jpg, png, webp, gif 이미지만 업로드할 수 있습니다.",
        )

    upload_root = Path(settings.upload_dir).resolve()
    image_dir = (upload_root / WORK_MANUAL_IMAGE_DIR).resolve()
    if upload_root not in image_dir.parents and image_dir != upload_root:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 저장 경로가 올바르지 않습니다.",
        )
    image_dir.mkdir(parents=True, exist_ok=True)

    filename = "{}{}".format(uuid4().hex, extension)
    destination = (image_dir / filename).resolve()
    if image_dir not in destination.parents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일명이 올바르지 않습니다.",
        )

    written_bytes = 0
    try:
        with destination.open("wb") as output:
            while True:
                chunk = await image.read(1024 * 1024)
                if not chunk:
                    break
                written_bytes += len(chunk)
                if written_bytes > MAX_IMAGE_SIZE_BYTES:
                    output.close()
                    destination.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="이미지는 10MB 이하만 업로드할 수 있습니다.",
                    )
                output.write(chunk)
    except HTTPException:
        raise
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="이미지 업로드에 실패했습니다.",
        ) from exc
    finally:
        await image.close()

    return WorkManualImageUploadResponse(
        url="/uploads/{}/{}".format(WORK_MANUAL_IMAGE_DIR, filename),
        filename=filename,
    )


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
    db: Session = Depends(get_db),
) -> WorkManualRead:
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
