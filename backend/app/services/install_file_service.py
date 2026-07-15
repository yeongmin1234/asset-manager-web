import re
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.config import BACKEND_DIR
from app.models.install_file import InstallFile


ALLOWED_INSTALL_FILE_EXTENSIONS = {
    ".exe",
    ".msi",
    ".zip",
    ".7z",
    ".pdf",
    ".txt",
    ".bat",
    ".ps1",
}
UPLOAD_CHUNK_SIZE = 1024 * 1024
logger = logging.getLogger(__name__)


class InstallFileNotFoundError(Exception):
    pass


class InstallFileValidationError(Exception):
    pass


class InstallFilePermissionError(Exception):
    pass


class InstallFileStorageError(Exception):
    pass


def _unlink_temporary_file(path: Path) -> None:
    try:
        if path.exists():
            path.unlink()
    except OSError:
        logger.exception("install_file_temporary_cleanup_failed")


def get_install_file_upload_dir() -> Path:
    configured = Path(settings.install_file_upload_dir)
    if configured.is_absolute():
        upload_dir = configured.resolve()
    else:
        upload_root = Path(settings.upload_dir)
        if not upload_root.is_absolute():
            upload_root = BACKEND_DIR / upload_root
        # The historic default points at ../uploads/install_files. Resolve it
        # through UPLOAD_DIR so Docker/NAS volume mappings remain authoritative.
        upload_dir = (upload_root / configured.name).resolve()
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        logger.error("upload_directory_permission_denied path=%s", upload_dir)
        raise InstallFilePermissionError("서버 저장 권한을 확인해주세요.") from exc
    except OSError as exc:
        logger.exception("install_file_upload_directory_error path=%s", upload_dir)
        raise InstallFileStorageError("설치자료 저장 중 오류가 발생했습니다.") from exc
    return upload_dir


def get_max_install_file_size() -> int:
    return int(settings.install_file_max_size_mb or 2048) * 1024 * 1024


def validate_original_filename(filename: str) -> str:
    original_filename = Path(filename or "").name.strip()
    if not original_filename:
        raise InstallFileValidationError("파일명을 확인해 주세요.")
    if original_filename != (filename or "").strip():
        raise InstallFileValidationError("파일명을 확인해 주세요.")
    if ".." in original_filename or "/" in original_filename or "\\" in original_filename:
        raise InstallFileValidationError("파일명을 확인해 주세요.")
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_INSTALL_FILE_EXTENSIONS:
        raise InstallFileValidationError("허용되지 않는 파일 형식입니다.")
    return original_filename


def build_stored_filename(original_filename: str) -> str:
    extension = Path(original_filename).suffix.lower()
    stem = Path(original_filename).stem
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-")
    if not safe_stem:
        safe_stem = "install_file"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return "{}_{}_{}{}".format(timestamp, uuid.uuid4().hex[:12], safe_stem[:80], extension)


def resolve_install_file_path(item: InstallFile) -> Path:
    upload_dir = get_install_file_upload_dir()
    stored_path = Path(item.file_path).resolve()
    if upload_dir != stored_path and upload_dir not in stored_path.parents:
        raise InstallFileValidationError("저장된 파일 경로를 확인할 수 없습니다.")
    return stored_path


async def save_install_upload(upload_file: UploadFile) -> dict:
    original_filename = validate_original_filename(upload_file.filename or "")
    stored_filename = build_stored_filename(original_filename)
    upload_dir = get_install_file_upload_dir()
    final_path = (upload_dir / stored_filename).resolve()
    if upload_dir != final_path and upload_dir not in final_path.parents:
        raise InstallFileValidationError("파일 저장 경로를 확인할 수 없습니다.")

    temp_path = final_path.with_suffix(final_path.suffix + ".uploading")
    file_size = 0
    max_size = get_max_install_file_size()
    try:
        with temp_path.open("wb") as file_handle:
            while True:
                chunk = await upload_file.read(UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                file_size += len(chunk)
                if file_size > max_size:
                    raise InstallFileValidationError("파일 크기가 허용 범위를 초과했습니다.")
                file_handle.write(chunk)
        temp_path.replace(final_path)
    except PermissionError as exc:
        logger.error("upload_directory_permission_denied path=%s", upload_dir)
        _unlink_temporary_file(temp_path)
        raise InstallFilePermissionError("서버 저장 권한을 확인해주세요.") from exc
    except InstallFileValidationError:
        _unlink_temporary_file(temp_path)
        raise
    except OSError as exc:
        _unlink_temporary_file(temp_path)
        logger.exception("install_file_storage_error path=%s", upload_dir)
        raise InstallFileStorageError("설치자료 저장 중 오류가 발생했습니다.") from exc
    finally:
        await upload_file.close()

    return {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_path": str(final_path),
        "file_size": file_size,
        "file_extension": Path(original_filename).suffix.lower(),
    }


def cleanup_install_upload(upload_data: Optional[dict]) -> None:
    """Remove only a newly written upload after its DB operation failed."""
    if not upload_data or not upload_data.get("file_path"):
        return
    try:
        upload_dir = get_install_file_upload_dir()
        target = Path(upload_data["file_path"]).resolve()
        if target != upload_dir and upload_dir in target.parents and target.is_file():
            target.unlink()
    except (OSError, InstallFilePermissionError, InstallFileStorageError):
        logger.exception("install_file_rollback_cleanup_failed")


def list_install_files(
    db: Session,
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    os_type: Optional[str] = None,
    is_required: Optional[bool] = None,
):
    statement = select(InstallFile).where(InstallFile.is_active.is_(True))
    if keyword:
        keyword_pattern = "%{}%".format(keyword.strip())
        statement = statement.where(
            InstallFile.title.ilike(keyword_pattern)
            | InstallFile.description.ilike(keyword_pattern)
            | InstallFile.original_filename.ilike(keyword_pattern)
        )
    if category:
        statement = statement.where(InstallFile.category == category)
    if os_type:
        statement = statement.where(InstallFile.os_type == os_type)
    if is_required is not None:
        statement = statement.where(InstallFile.is_required.is_(is_required))
    statement = statement.order_by(
        InstallFile.is_required.desc(),
        InstallFile.install_order.asc(),
        InstallFile.created_at.desc(),
    )
    return list(db.scalars(statement).all())


def get_install_file(db: Session, file_id: int) -> InstallFile:
    item = db.get(InstallFile, file_id)
    if item is None or not item.is_active:
        raise InstallFileNotFoundError()
    return item


def create_install_file(db: Session, file_data: dict, upload_data: dict) -> InstallFile:
    item = InstallFile(**file_data, **upload_data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_install_file(
    db: Session,
    file_id: int,
    file_data: dict,
    upload_data: Optional[dict] = None,
) -> InstallFile:
    item = get_install_file(db, file_id)
    old_path = None
    if upload_data:
        old_path = resolve_install_file_path(item)
    for key, value in file_data.items():
        setattr(item, key, value)
    if upload_data:
        for key, value in upload_data.items():
            setattr(item, key, value)
    db.add(item)
    db.commit()
    db.refresh(item)
    if old_path and old_path.exists() and old_path != resolve_install_file_path(item):
        try:
            old_path.unlink()
        except OSError:
            pass
    return item


def delete_install_file(db: Session, file_id: int) -> InstallFile:
    item = get_install_file(db, file_id)
    item.is_active = False
    db.add(item)
    db.commit()
    db.refresh(item)
    file_path = resolve_install_file_path(item)
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    return item


def increment_install_file_download_count(db: Session, item: InstallFile) -> InstallFile:
    item.download_count = int(item.download_count or 0) + 1
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def get_install_file_summary(db: Session) -> dict:
    statement = select(
        func.count(InstallFile.id),
        func.coalesce(func.sum(InstallFile.file_size), 0),
        func.coalesce(func.sum(InstallFile.download_count), 0),
    ).where(InstallFile.is_active.is_(True))
    total_count, total_size, total_download_count = db.execute(statement).one()
    required_count = db.scalar(
        select(func.count(InstallFile.id)).where(
            InstallFile.is_active.is_(True),
            InstallFile.is_required.is_(True),
        )
    )
    return {
        "total_count": int(total_count or 0),
        "required_count": int(required_count or 0),
        "total_size": int(total_size or 0),
        "total_download_count": int(total_download_count or 0),
    }
