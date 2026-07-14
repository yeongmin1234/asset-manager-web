import logging
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.schemas.hr_account import (
    HrAccountCreate, HrAccountImportPreviewResponse, HrAccountImportRequest,
    HrAccountImportResponse, HrAccountRead, HrAccountUpdate,
)
from app.services.hr_account_service import (
    HrAccountImportValidationError, HrAccountNotFoundError,
    build_hr_account_import_template, create_hr_account, delete_hr_account,
    import_hr_accounts, list_hr_accounts, preview_hr_accounts_import,
    update_hr_account,
)

router = APIRouter(prefix="/hr/accounts", tags=["hr-accounts"])
logger = logging.getLogger(__name__)
MAX_HR_IMPORT_FILE_SIZE = 5 * 1024 * 1024


@router.get("", response_model=List[HrAccountRead])
def read_hr_accounts(keyword: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    try:
        return list_hr_accounts(db, keyword)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="계정 현황을 불러오는 중 DB 연결에 실패했습니다.") from exc


@router.post("", response_model=HrAccountRead, status_code=status.HTTP_201_CREATED)
def create_new_hr_account(request: Request, payload: HrAccountCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = create_hr_account(db, payload)
        record_audit_log(db, request, current_user, action_type="create", menu_key="hr_list", menu_name="인사업무 > 리스트", target_type="hr_account", target_id=result.id, target_name=result.name, action_summary="인사업무 계정을 등록했습니다.")
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 등록하는 중 DB 연결에 실패했습니다.") from exc


@router.get("/import/template")
def download_hr_account_import_template() -> StreamingResponse:
    filename = "인사업무_계정등록_양식.xlsx"
    return StreamingResponse(
        build_hr_account_import_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename*=UTF-8''{}".format(quote(filename))},
    )


@router.post("/import/preview", response_model=HrAccountImportPreviewResponse)
async def preview_hr_account_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> HrAccountImportPreviewResponse:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=".xlsx 파일만 업로드할 수 있습니다.")
    file_bytes = await file.read(MAX_HR_IMPORT_FILE_SIZE + 1)
    if len(file_bytes) > MAX_HR_IMPORT_FILE_SIZE:
        raise HTTPException(status_code=413, detail="엑셀 파일은 최대 5MB까지 업로드할 수 있습니다.")
    try:
        return preview_hr_accounts_import(db, file_bytes)
    except HrAccountImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        logger.exception("HR account Excel preview database error")
        raise HTTPException(status_code=503, detail="엑셀 미리보기 중 DB 연결에 실패했습니다.") from exc


@router.post("/import", response_model=HrAccountImportResponse)
def commit_hr_account_import(
    request: Request,
    payload: HrAccountImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HrAccountImportResponse:
    try:
        result = import_hr_accounts(db, payload.rows, payload.duplicate_policy)
        summary = "엑셀 계정 {}건을 등록했습니다. 중복 업데이트 {}건, 건너뜀 {}건.".format(result.created_count, result.updated_count, result.skipped_count)
        record_audit_log(db, request, current_user, action_type="excel_import", menu_key="hr_list", menu_name="인사업무 > 리스트", target_type="hr_account_import", target_id=None, target_name="인사업무 계정 엑셀 일괄등록", action_summary=summary)
        return result
    except HrAccountImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("HR account Excel import database error")
        raise HTTPException(status_code=503, detail="엑셀 일괄등록 중 DB 연결에 실패했습니다.") from exc


@router.put("/{account_id}", response_model=HrAccountRead)
def update_existing_hr_account(request: Request, account_id: int, payload: HrAccountUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = update_hr_account(db, account_id, payload)
        record_audit_log(db, request, current_user, action_type="update", menu_key="hr_list", menu_name="인사업무 > 리스트", target_type="hr_account", target_id=result.id, target_name=result.name, action_summary="인사업무 계정을 수정했습니다.")
        return result
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 수정하는 중 DB 연결에 실패했습니다.") from exc


@router.delete("/{account_id}", response_model=HrAccountRead)
def delete_existing_hr_account(request: Request, account_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = delete_hr_account(db, account_id)
        record_audit_log(db, request, current_user, action_type="delete", menu_key="hr_list", menu_name="인사업무 > 리스트", target_type="hr_account", target_id=result.id, target_name=result.name, action_summary="인사업무 계정을 삭제했습니다.")
        return result
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 삭제하는 중 DB 연결에 실패했습니다.") from exc
