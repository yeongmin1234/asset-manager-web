import mimetypes
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_DIR, settings
from app.models.asset import Asset
from app.models.attachment import Attachment, AttachmentEntityType
from app.models.company_vehicle import CompanyVehicle
from app.models.expiration_schedule import ExpirationSchedule
from app.models.paju_fire_insurance import PajuFireInsuranceContract
from app.models.user import User
from app.models.vendor_contact import VendorContact
from app.models.work_manual import WorkManual
from app.services.activity_log_service import record_activity_log


UPLOAD_CHUNK_SIZE = 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".xlsx",
    ".xls",
    ".docx",
    ".doc",
    ".pptx",
    ".ppt",
    ".txt",
    ".zip",
}
BLOCKED_ATTACHMENT_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".ps1",
    ".sh",
    ".js",
    ".html",
    ".php",
    ".py",
    ".dll",
    ".msi",
}
ENTITY_FOLDER_MAP = {
    AttachmentEntityType.ASSET: "assets",
    AttachmentEntityType.VENDOR_CONTACT: "vendor_contacts",
    AttachmentEntityType.WORK_MANUAL: "work_manuals",
    AttachmentEntityType.COMPANY_CAR: "company_cars",
    AttachmentEntityType.FIRE_INSURANCE: "fire_insurance",
    AttachmentEntityType.EXPIRATION_SCHEDULE: "expiration_schedules",
}
ENTITY_PERMISSION_MAP = {
    AttachmentEntityType.ASSET: "assets",
    AttachmentEntityType.VENDOR_CONTACT: "vendor-contacts",
    AttachmentEntityType.WORK_MANUAL: "work-manuals",
    AttachmentEntityType.COMPANY_CAR: "vehicles",
    AttachmentEntityType.FIRE_INSURANCE: "paju-fire-insurance",
    AttachmentEntityType.EXPIRATION_SCHEDULE: "expiration_schedules",
}
ENTITY_MODEL_MAP = {
    AttachmentEntityType.ASSET: Asset,
    AttachmentEntityType.VENDOR_CONTACT: VendorContact,
    AttachmentEntityType.WORK_MANUAL: WorkManual,
    AttachmentEntityType.COMPANY_CAR: CompanyVehicle,
    AttachmentEntityType.FIRE_INSURANCE: PajuFireInsuranceContract,
    AttachmentEntityType.EXPIRATION_SCHEDULE: ExpirationSchedule,
}
ENTITY_MENU_NAME_MAP = {
    AttachmentEntityType.ASSET: "자산 관리",
    AttachmentEntityType.VENDOR_CONTACT: "업체연락처",
    AttachmentEntityType.WORK_MANUAL: "업무설명서",
    AttachmentEntityType.COMPANY_CAR: "법인차량 관리",
    AttachmentEntityType.FIRE_INSURANCE: "파주화재보험",
    AttachmentEntityType.EXPIRATION_SCHEDULE: "점검·만료 관리",
}
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
PDF_MIME_TYPES = {"application/pdf"}
PREVIEW_MIME_TYPES = IMAGE_MIME_TYPES | PDF_MIME_TYPES


class AttachmentNotFoundError(Exception):
    pass


class AttachmentValidationError(Exception):
    pass


def list_attachments(
    db: Session,
    *,
    entity_type: Optional[AttachmentEntityType] = None,
    entity_id: Optional[int] = None,
) -> List[Attachment]:
    statement = select(Attachment)
    if entity_type is not None:
        statement = statement.where(Attachment.entity_type == entity_type)
    if entity_id is not None:
        statement = statement.where(Attachment.entity_id == entity_id)
    statement = statement.order_by(Attachment.created_at.desc(), Attachment.id.desc())
    return [_prepare_attachment(item) for item in db.scalars(statement).all()]


def get_attachment(db: Session, attachment_id: int) -> Attachment:
    attachment = db.get(Attachment, attachment_id)
    if attachment is None:
        raise AttachmentNotFoundError()
    return _prepare_attachment(attachment)


async def create_attachment(
    db: Session,
    *,
    entity_type: AttachmentEntityType,
    entity_id: int,
    upload_file: UploadFile,
    description: Optional[str],
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Attachment:
    ensure_entity_exists(db, entity_type, entity_id)
    original_filename, extension = validate_original_filename(upload_file.filename or "")
    content_type = normalize_mime_type(upload_file.content_type, original_filename)
    validate_mime_type(extension, content_type)
    folder_name = ENTITY_FOLDER_MAP[entity_type]
    stored_filename = "{}{}".format(uuid.uuid4().hex, extension)
    attachment_root_name = (settings.attachment_upload_dir or "attachments").strip().strip("/\\") or "attachments"
    relative_path = str(Path(attachment_root_name) / folder_name / stored_filename).replace("\\", "/")
    final_path = resolve_upload_relative_path(relative_path)
    temp_path = final_path.with_suffix(final_path.suffix + ".uploading")
    max_size = get_max_attachment_size()
    file_size = 0
    try:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        with temp_path.open("wb") as file_handle:
            while True:
                chunk = await upload_file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > max_size:
                    raise AttachmentValidationError("파일 크기는 20MB 이하만 업로드할 수 있습니다.")
                file_handle.write(chunk)
        temp_path.replace(final_path)
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise
    finally:
        await upload_file.close()

    attachment = Attachment(
        entity_type=entity_type,
        entity_id=entity_id,
        original_filename=original_filename,
        stored_filename=stored_filename,
        relative_path=relative_path,
        mime_type=content_type,
        file_size=file_size,
        description=(description or "").strip() or None,
        uploaded_by=get_user_label(current_user),
    )
    db.add(attachment)
    db.flush()
    record_attachment_activity(
        db,
        attachment,
        action_type="upload",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
    )
    db.commit()
    db.refresh(attachment)
    return _prepare_attachment(attachment)


def delete_attachment(
    db: Session,
    attachment_id: int,
    *,
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Attachment:
    attachment = get_attachment(db, attachment_id)
    file_path = resolve_attachment_path(attachment)
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
        except OSError as exc:
            raise AttachmentValidationError("첨부파일 원본 삭제에 실패했습니다.") from exc
    elif file_path.exists():
        raise AttachmentValidationError("첨부파일 경로를 확인할 수 없습니다.")

    deleted_attachment = _prepare_attachment(attachment)
    record_attachment_activity(
        db,
        attachment,
        action_type="delete",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
    )
    db.delete(attachment)
    db.commit()
    return deleted_attachment


def resolve_attachment_path(attachment: Attachment) -> Path:
    return resolve_upload_relative_path(attachment.relative_path)


def resolve_upload_relative_path(relative_path: str) -> Path:
    upload_root = get_upload_root()
    normalized = Path(relative_path)
    if normalized.is_absolute() or ".." in normalized.parts:
        raise AttachmentValidationError("첨부파일 경로를 확인할 수 없습니다.")
    resolved_path = (upload_root / normalized).resolve()
    if upload_root != resolved_path and upload_root not in resolved_path.parents:
        raise AttachmentValidationError("첨부파일 경로를 확인할 수 없습니다.")
    return resolved_path


def get_upload_root() -> Path:
    configured = Path(settings.upload_dir)
    upload_root = configured if configured.is_absolute() else BACKEND_DIR / configured
    return upload_root.resolve()


def get_max_attachment_size() -> int:
    return int(settings.attachment_max_size_mb or 20) * 1024 * 1024


def validate_original_filename(filename: str) -> Tuple[str, str]:
    original_filename = Path(filename or "").name.strip()
    if not original_filename:
        raise AttachmentValidationError("파일명을 확인해 주세요.")
    if original_filename != (filename or "").strip():
        raise AttachmentValidationError("파일명을 확인해 주세요.")
    if ".." in original_filename or "/" in original_filename or "\\" in original_filename:
        raise AttachmentValidationError("파일명을 확인해 주세요.")
    extension = Path(original_filename).suffix.lower()
    if extension in BLOCKED_ATTACHMENT_EXTENSIONS or extension not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise AttachmentValidationError("허용되지 않는 파일 형식입니다.")
    return original_filename, extension


def normalize_mime_type(content_type: Optional[str], filename: str) -> str:
    guessed_type = mimetypes.guess_type(filename)[0] or ""
    normalized = (content_type or guessed_type or "application/octet-stream").split(";")[0].strip().lower()
    return normalized or "application/octet-stream"


def validate_mime_type(extension: str, mime_type: str) -> None:
    allowed_prefixes = {
        ".pdf": ("application/pdf",),
        ".png": ("image/png",),
        ".jpg": ("image/jpeg",),
        ".jpeg": ("image/jpeg",),
        ".webp": ("image/webp",),
        ".txt": ("text/plain", "application/octet-stream"),
        ".zip": ("application/zip", "application/x-zip-compressed", "application/octet-stream"),
        ".xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/octet-stream"),
        ".xls": ("application/vnd.ms-excel", "application/octet-stream"),
        ".docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/octet-stream"),
        ".doc": ("application/msword", "application/octet-stream"),
        ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", "application/octet-stream"),
        ".ppt": ("application/vnd.ms-powerpoint", "application/octet-stream"),
    }
    allowed_mime_types = allowed_prefixes.get(extension, ())
    if mime_type not in allowed_mime_types:
        raise AttachmentValidationError("파일 MIME type을 확인해 주세요.")


def can_preview_attachment(attachment: Attachment) -> bool:
    return (attachment.mime_type or "").lower() in PREVIEW_MIME_TYPES


def ensure_entity_exists(db: Session, entity_type: AttachmentEntityType, entity_id: int) -> None:
    model = ENTITY_MODEL_MAP[entity_type]
    item = db.get(model, entity_id)
    if item is None:
        raise AttachmentValidationError("첨부 대상 데이터를 찾을 수 없습니다.")
    if hasattr(item, "deleted_at") and getattr(item, "deleted_at") is not None:
        raise AttachmentValidationError("삭제된 데이터에는 첨부할 수 없습니다.")
    if hasattr(item, "is_deleted") and getattr(item, "is_deleted"):
        raise AttachmentValidationError("삭제된 데이터에는 첨부할 수 없습니다.")
    if hasattr(item, "is_active") and getattr(item, "is_active") is False:
        raise AttachmentValidationError("비활성 데이터에는 첨부할 수 없습니다.")


def ensure_attachment_access(user: User, entity_type: AttachmentEntityType) -> None:
    if user.role == "admin":
        return
    permission = ENTITY_PERMISSION_MAP[entity_type]
    if permission not in set(user.menu_permissions or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="첨부파일 접근 권한이 없습니다.",
        )


def ensure_no_attachments(db: Session, entity_type: AttachmentEntityType, entity_id: int) -> None:
    count = db.scalar(
        select(func.count(Attachment.id)).where(
            Attachment.entity_type == entity_type,
            Attachment.entity_id == entity_id,
        )
    )
    if count:
        raise AttachmentValidationError("연결된 첨부파일이 있어 먼저 첨부파일을 삭제해 주세요.")


def record_attachment_activity(
    db: Session,
    attachment: Attachment,
    *,
    action_type: str,
    current_user: User,
    actor_ip: Optional[str],
    user_agent: Optional[str],
) -> None:
    label = "파일 업로드" if action_type == "upload" else "파일 삭제"
    record_activity_log(
        db,
        menu_name=ENTITY_MENU_NAME_MAP[attachment.entity_type],
        action_type=action_type,
        target_type="attachment",
        target_id=attachment.id,
        target_name=attachment.original_filename,
        actor_ip=actor_ip,
        actor_name=get_user_label(current_user),
        user_agent=user_agent,
        summary="{}: {}".format(label, attachment.original_filename),
        before_data=None if action_type == "upload" else serialize_attachment(attachment),
        after_data=serialize_attachment(attachment) if action_type == "upload" else None,
    )


def serialize_attachment(attachment: Attachment) -> Dict[str, object]:
    return {
        "entity_type": attachment.entity_type.value if hasattr(attachment.entity_type, "value") else attachment.entity_type,
        "entity_id": attachment.entity_id,
        "original_filename": attachment.original_filename,
        "mime_type": attachment.mime_type,
        "file_size": attachment.file_size,
        "description": attachment.description,
        "uploaded_by": attachment.uploaded_by,
    }


def _prepare_attachment(attachment: Attachment) -> Attachment:
    attachment.uploader_name = attachment.uploaded_by
    return attachment


def get_user_label(user: User) -> str:
    return user.name or user.username
