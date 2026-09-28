"""Read-only Excel preview for online TEAM recall applications."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder

from app.core.auth import get_current_user
from app.models.user import User
from app.services.recall_application_excel import (
    RecallApplicationExcelError,
    preview_recall_applications,
)


router = APIRouter(prefix="/online/recall/applications", tags=["online-recall"])
MAX_PREVIEW_FILE_SIZE = 5 * 1024 * 1024


def require_recall_preview_access(user: User = Depends(get_current_user)) -> User:
    # The online TEAM screens currently follow the existing dashboard permission.
    # This endpoint parses only; it never creates or updates business records.
    if user.role != "admin" and "dashboard" not in (user.menu_permissions or []):
        raise HTTPException(status_code=403, detail="이 메뉴에 접근할 권한이 없습니다.")
    return user


@router.post("/preview")
async def preview_recall_application_excel(
    file: UploadFile = File(...),
    _user: User = Depends(require_recall_preview_access),
):
    try:
        if not (file.filename or "").lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail=".xlsx 파일만 선택할 수 있습니다.")

        file_bytes = await file.read(MAX_PREVIEW_FILE_SIZE + 1)
        if len(file_bytes) > MAX_PREVIEW_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Excel 파일은 최대 5MB까지 미리볼 수 있습니다.")

        try:
            preview = preview_recall_applications(file_bytes, source_filename=file.filename)
        except RecallApplicationExcelError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            # Workbook parsing may fail after its ZIP container has opened.
            # Do not include source cell values or traceback in the response.
            raise HTTPException(status_code=400, detail="Excel 파일을 분석할 수 없습니다.") from exc

        counts = preview.counts()
        return jsonable_encoder({
            "sheet_name": preview.sheet_name,
            "matched_columns": preview.matched_columns,
            "summary": {
                "total_rows": len(preview.rows),  # header excluded, blank/instruction included
                "valid": counts["valid"],
                "duplicate": counts["duplicate"],
                "error": counts["error"],
                "review": counts["review"],
                "excluded": counts["blank"] + counts["instruction"],
            },
            "rows": [asdict(row) for row in preview.rows],
        })
    finally:
        await file.close()
