import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.work_manual import WorkManual
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
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
from app.services.attachment_service import AttachmentValidationError
from app.services.private_file_response import private_file_response


router = APIRouter(prefix="/work-manuals", tags=["work-manuals"])
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
WORK_MANUAL_IMAGE_DIR = "work_manuals/images"
WORK_MANUAL_IMAGE_URL_PREFIX = "/uploads/work_manuals/images/"
PROTECTED_IMAGE_URL_PREFIX = "/work-manuals/images/"
STORED_IMAGE_NAME_PATTERN = re.compile(r"[a-f0-9]{32}\.(?:jpg|jpeg|png|webp|gif)", re.IGNORECASE)
BASE64_IMAGE_PATTERN = re.compile(r"data:image/[a-z0-9.+-]+;base64,[^\s\"'<)]+", re.IGNORECASE)
DANGEROUS_CONTENT_TAGS = {"script", "iframe", "object", "embed", "style"}
SAFE_CONTENT_TAGS = {"p", "div", "strong", "b", "em", "i", "u", "h2", "h3", "ul", "ol", "li"}
VOID_CONTENT_TAGS = {"br", "hr"}


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
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="jpg, jpeg, png, webp, gif 이미지만 업로드할 수 있습니다.",
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
        url="{}{}".format(PROTECTED_IMAGE_URL_PREFIX, filename),
        filename=filename,
    )


@router.get("/images/{filename}")
def read_work_manual_image(
    request: Request,
    filename: str,
    current_user: User = Depends(get_current_user),
) -> FileResponse:
    if not STORED_IMAGE_NAME_PATTERN.fullmatch(filename):
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    image_dir = (Path(settings.upload_dir).resolve() / WORK_MANUAL_IMAGE_DIR).resolve()
    path = (image_dir / filename).resolve()
    if image_dir not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    suffix = path.suffix.lower()
    media_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/" + suffix.lstrip(".")
    return private_file_response(path, request=request, user_id=current_user.id,
                                 file_id=filename.split(".", 1)[0], file_kind="work_manual_image",
                                 media_type=media_type, inline=True)


@router.get("/{manual_id}", response_model=WorkManualRead)
def read_work_manual(manual_id: int, db: Session = Depends(get_db)) -> WorkManualRead:
    try:
        return get_work_manual(db, manual_id, increment_view_count=True)
    except WorkManualNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="업무설명서를 찾을 수 없습니다.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=WorkManualRead, status_code=status.HTTP_201_CREATED)
def create_new_work_manual(
    request: Request,
    payload: WorkManualCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkManualRead:
    try:
        sanitized_payload = payload.model_copy(update={"content": sanitize_work_manual_content(payload.content)})
        result = create_work_manual(db, sanitized_payload)
        record_audit_log(db, request, current_user, action_type="create", menu_key="work_manual", menu_name="업무설명서", target_type="work_manual", target_id=result.id, target_name=result.title, action_summary="업무설명서를 등록했습니다.", after_data=audit_snapshot(result, ("title", "category")))
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="업무설명서를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{manual_id}", response_model=WorkManualRead)
def update_existing_work_manual(
    request: Request,
    manual_id: int,
    payload: WorkManualUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkManualRead:
    try:
        fields = ("title", "category", "content")
        before = audit_snapshot(db.get(WorkManual, manual_id), fields)
        sanitized_payload = payload.model_copy(update={"content": sanitize_work_manual_content(payload.content)})
        result = update_work_manual(db, manual_id, sanitized_payload)
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="work_manual", menu_name="업무설명서", target_type="work_manual", target_id=result.id, target_name=result.title, action_summary="업무설명서를 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
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
    request: Request,
    manual_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WorkManualRead:
    try:
        before = audit_snapshot(db.get(WorkManual, manual_id), ("title", "category"))
        result = delete_work_manual(db, manual_id)
        record_audit_log(db, request, current_user, action_type="delete", menu_key="work_manual", menu_name="업무설명서", target_type="work_manual", target_id=result.id, target_name=result.title, action_summary="업무설명서를 삭제했습니다.", before_data=before)
        return result
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


class WorkManualHtmlSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag_name = tag.lower()
        if tag_name in DANGEROUS_CONTENT_TAGS:
            self.blocked_depth += 1
            return
        if self.blocked_depth:
            return
        if tag_name in VOID_CONTENT_TAGS:
            self.parts.append("<{}>".format(tag_name))
            return
        if tag_name == "img":
            attr_map = {name.lower(): value for name, value in attrs if name and value is not None}
            src = attr_map.get("src", "")
            if not is_safe_work_manual_image_url(src):
                return
            alt = escape(attr_map.get("alt") or "이미지", quote=True)
            self.parts.append('<img src="{}" alt="{}">'.format(escape(src, quote=True), alt))
            return
        if tag_name in SAFE_CONTENT_TAGS:
            self.parts.append("<{}>".format(tag_name))

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if tag_name in DANGEROUS_CONTENT_TAGS:
            self.blocked_depth = max(0, self.blocked_depth - 1)
            return
        if self.blocked_depth:
            return
        if tag_name in SAFE_CONTENT_TAGS:
            self.parts.append("</{}>".format(tag_name))

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.parts.append(escape(data, quote=False))


def sanitize_work_manual_content(content: str) -> str:
    html = BASE64_IMAGE_PATTERN.sub("", content or "")
    sanitizer = WorkManualHtmlSanitizer()
    sanitizer.feed(html)
    sanitizer.close()
    return "".join(sanitizer.parts).strip()


def is_safe_work_manual_image_url(url: str) -> bool:
    normalized_url = str(url or "")
    for prefix in (WORK_MANUAL_IMAGE_URL_PREFIX, PROTECTED_IMAGE_URL_PREFIX):
        if normalized_url.startswith(prefix):
            return STORED_IMAGE_NAME_PATTERN.fullmatch(normalized_url[len(prefix):]) is not None
    return False
