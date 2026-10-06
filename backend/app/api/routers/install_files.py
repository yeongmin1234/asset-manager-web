from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import require_admin
from app.models.user import User
from app.models.install_file import InstallFile
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log
from app.services.private_file_response import private_file_response
from app.schemas.install_file import (
    InstallFileDeleteRequest,
    InstallFileListResponse,
    InstallFileRead,
    InstallFileSummary,
)
from app.services.admin_service import (
    is_admin_password_configured,
    verify_admin_password,
)
from app.services.install_file_service import (
    InstallFileNotFoundError,
    InstallFilePermissionError,
    InstallFileStorageError,
    InstallFileValidationError,
    cleanup_install_upload,
    create_install_file,
    delete_install_file,
    get_install_file,
    get_install_file_summary,
    increment_install_file_download_count,
    list_install_files,
    resolve_install_file_path,
    save_install_upload,
    update_install_file,
)


router = APIRouter(prefix="/install-files", tags=["install-files"])


def verify_admin_guard(db: Session, admin_password: str) -> None:
    if not is_admin_password_configured(db):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="관리자 비밀번호가 설정되지 않았습니다.",
        )
    if not verify_admin_password(db, admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="관리자 비밀번호를 확인해 주세요.",
        )


def build_file_data(
    title: str,
    category: str,
    os_type: str,
    version: str,
    description: str,
    install_guide: str,
    caution_note: str,
    is_required: bool,
    install_order: int,
) -> dict:
    cleaned_title = (title or "").strip()
    if not cleaned_title:
        raise InstallFileValidationError("제목을 입력해 주세요.")
    return {
        "title": cleaned_title,
        "category": (category or "기타").strip() or "기타",
        "os_type": (os_type or "전체").strip() or "전체",
        "version": (version or "").strip() or None,
        "description": (description or "").strip() or None,
        "install_guide": (install_guide or "").strip() or None,
        "caution_note": (caution_note or "").strip() or None,
        "is_required": bool(is_required),
        "install_order": int(install_order or 0),
    }


@router.get("", response_model=InstallFileListResponse)
def read_install_files(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    os_type: Optional[str] = None,
    is_required: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> InstallFileListResponse:
    try:
        items = list_install_files(
            db,
            keyword=keyword,
            category=category,
            os_type=os_type,
            is_required=is_required,
        )
        return InstallFileListResponse(items=items, total=len(items))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료 목록을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/summary", response_model=InstallFileSummary)
def read_install_file_summary(db: Session = Depends(get_db)) -> InstallFileSummary:
    try:
        return InstallFileSummary(**get_install_file_summary(db))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료 요약을 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/{file_id}", response_model=InstallFileRead)
def read_install_file(file_id: int, db: Session = Depends(get_db)) -> InstallFileRead:
    try:
        return get_install_file(db, file_id)
    except InstallFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설치자료를 찾을 수 없습니다.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료를 불러오는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.post("", response_model=InstallFileRead, status_code=status.HTTP_201_CREATED)
async def create_new_install_file(
    request: Request,
    title: str = Form(...),
    category: str = Form("기타"),
    os_type: str = Form("전체"),
    version: str = Form(""),
    description: str = Form(""),
    install_guide: str = Form(""),
    caution_note: str = Form(""),
    is_required: bool = Form(False),
    install_order: int = Form(0),
    admin_password: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> InstallFileRead:
    verify_admin_guard(db, admin_password)
    upload_data = None
    try:
        file_data = build_file_data(
            title,
            category,
            os_type,
            version,
            description,
            install_guide,
            caution_note,
            is_required,
            install_order,
        )
        upload_data = await save_install_upload(file)
        result = create_install_file(db, file_data, upload_data)
        record_audit_log(db, request, current_admin, action_type="create", menu_key="install_files", menu_name="설치자료실", target_type="install_file", target_id=result.id, target_name=result.title, action_summary="설치자료를 등록했습니다.", after_data=audit_snapshot(result, ("title", "category", "os_type", "version", "is_required", "original_filename")))
        return result
    except InstallFileValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InstallFilePermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except InstallFileStorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        cleanup_install_upload(upload_data)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료를 등록하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.put("/{file_id}", response_model=InstallFileRead)
async def update_existing_install_file(
    request: Request,
    file_id: int,
    title: str = Form(...),
    category: str = Form("기타"),
    os_type: str = Form("전체"),
    version: str = Form(""),
    description: str = Form(""),
    install_guide: str = Form(""),
    caution_note: str = Form(""),
    is_required: bool = Form(False),
    install_order: int = Form(0),
    admin_password: str = Form(...),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> InstallFileRead:
    verify_admin_guard(db, admin_password)
    upload_data = None
    try:
        fields = ("title", "category", "os_type", "version", "is_required", "install_order", "original_filename")
        before = audit_snapshot(get_install_file(db, file_id), fields)
        file_data = build_file_data(
            title,
            category,
            os_type,
            version,
            description,
            install_guide,
            caution_note,
            is_required,
            install_order,
        )
        upload_data = None
        if file is not None and file.filename:
            upload_data = await save_install_upload(file)
        result = update_install_file(db, file_id, file_data, upload_data)
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_admin, action_type="update", menu_key="install_files", menu_name="설치자료실", target_type="install_file", target_id=result.id, target_name=result.title, action_summary="설치자료 정보를 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except InstallFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설치자료를 찾을 수 없습니다.",
        ) from exc
    except InstallFileValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except InstallFilePermissionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except InstallFileStorageError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        cleanup_install_upload(upload_data)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료를 수정하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.delete("/{file_id}", response_model=InstallFileRead)
def delete_existing_install_file(
    request: Request,
    file_id: int,
    payload: InstallFileDeleteRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> InstallFileRead:
    verify_admin_guard(db, payload.admin_password)
    try:
        before = audit_snapshot(db.get(InstallFile, file_id), ("title", "category", "os_type", "version", "is_required", "original_filename"))
        result = delete_install_file(db, file_id)
        record_audit_log(db, request, current_admin, action_type="delete", menu_key="install_files", menu_name="설치자료실", target_type="install_file", target_id=result.id, target_name=result.title, action_summary="설치자료를 삭제했습니다.", before_data=before)
        return result
    except InstallFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설치자료를 찾을 수 없습니다.",
        ) from exc
    except InstallFileValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료를 삭제하는 중 DB 연결에 실패했습니다.",
        ) from exc


@router.get("/{file_id}/download")
def download_install_file(request: Request, file_id: int, db: Session = Depends(get_db),
                          current_admin: User = Depends(require_admin)) -> FileResponse:
    try:
        item = get_install_file(db, file_id)
        request.state.download_filename = item.original_filename
        file_path = resolve_install_file_path(item)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="설치자료 파일을 찾을 수 없습니다.",
            )
        item = increment_install_file_download_count(db, item)
        return private_file_response(file_path, request=request,
                                     user_id=current_admin.id,
                                     file_id=str(file_id), file_kind="install_file",
                                     media_type="application/octet-stream",
                                     filename=item.original_filename)
    except InstallFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="설치자료를 찾을 수 없습니다.",
        ) from exc
    except InstallFileValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="설치자료 다운로드 중 DB 연결에 실패했습니다.",
        ) from exc
