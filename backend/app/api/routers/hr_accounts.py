import logging
from typing import List, Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
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
def create_new_hr_account(payload: HrAccountCreate, db: Session = Depends(get_db)):
    try:
        return create_hr_account(db, payload)
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
    payload: HrAccountImportRequest,
    db: Session = Depends(get_db),
) -> HrAccountImportResponse:
    try:
        return import_hr_accounts(db, payload.rows, payload.duplicate_policy)
    except HrAccountImportValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("HR account Excel import database error")
        raise HTTPException(status_code=503, detail="엑셀 일괄등록 중 DB 연결에 실패했습니다.") from exc


@router.put("/{account_id}", response_model=HrAccountRead)
def update_existing_hr_account(account_id: int, payload: HrAccountUpdate, db: Session = Depends(get_db)):
    try:
        return update_hr_account(db, account_id, payload)
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 수정하는 중 DB 연결에 실패했습니다.") from exc


@router.delete("/{account_id}", response_model=HrAccountRead)
def delete_existing_hr_account(account_id: int, db: Session = Depends(get_db)):
    try:
        return delete_hr_account(db, account_id)
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 삭제하는 중 DB 연결에 실패했습니다.") from exc
