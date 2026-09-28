"""Preview, register, and read APIs for online TEAM recall applications."""

import json
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.services.recall_application_excel import RecallApplicationExcelError, preview_recall_applications
from app.services.recall_application_service import (
    commit_recall_applications,
    existing_application_records,
    get_recall_application_detail,
    get_recall_summary,
    list_recall_applications,
    change_recall_application_status,
)


router = APIRouter(prefix="/online/recall/applications", tags=["online-recall"])
MAX_PREVIEW_FILE_SIZE = 5 * 1024 * 1024


class RecallStatusChangeRequest(BaseModel):
    status: str
    reason: str


def require_recall_preview_access(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    if user.role != "admin" and "online_recall" not in (user.menu_permissions or []):
        raise HTTPException(status_code=403, detail="이 메뉴에 접근할 권한이 없습니다.")
    visibility = db.scalar(
        select(MenuVisibilitySetting.visible).where(MenuVisibilitySetting.menu_key == "online_recall")
    )
    if visibility is False:
        raise HTTPException(status_code=403, detail="현재 숨김 처리된 메뉴입니다.")
    return user


async def _read_xlsx(file: UploadFile) -> bytes:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=".xlsx 파일만 선택할 수 있습니다.")
    file_bytes = await file.read(MAX_PREVIEW_FILE_SIZE + 1)
    if len(file_bytes) > MAX_PREVIEW_FILE_SIZE:
        raise HTTPException(status_code=413, detail="Excel 파일은 최대 5MB까지 처리할 수 있습니다.")
    return file_bytes


def _preview_response(preview):
    counts = preview.counts()
    return jsonable_encoder({
        "sheet_name": preview.sheet_name,
        "matched_columns": preview.matched_columns,
        "summary": {
            "total_rows": len(preview.rows),
            "valid": counts["valid"],
            "duplicate": counts["duplicate"],
            "error": counts["error"],
            "review": counts["review"],
            "excluded": counts["blank"] + counts["instruction"],
        },
        "rows": [asdict(row) for row in preview.rows],
    })


@router.post("/preview")
async def preview_recall_application_excel(
    file: UploadFile = File(...),
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        file_bytes = await _read_xlsx(file)
        try:
            preview = preview_recall_applications(
                file_bytes,
                source_filename=file.filename,
                existing_records=existing_application_records(db),
            )
        except RecallApplicationExcelError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Excel 파일을 분석할 수 없습니다.") from exc
        return _preview_response(preview)
    finally:
        await file.close()


@router.post("/commit")
async def commit_recall_application_excel(
    request: Request,
    file: UploadFile = File(...),
    selected_row_numbers: str = Form(...),
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        file_bytes = await _read_xlsx(file)
        try:
            parsed_selection = json.loads(selected_row_numbers)
            if not isinstance(parsed_selection, list) or any(type(value) is not int for value in parsed_selection):
                raise ValueError
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            raise HTTPException(status_code=400, detail="등록할 행 선택값이 올바르지 않습니다.") from exc

        try:
            result = commit_recall_applications(
                db,
                file_bytes=file_bytes,
                source_filename=file.filename or "recall-applications.xlsx",
                selected_row_numbers=parsed_selection,
                user_id=current_user.id,
            )
        except RecallApplicationExcelError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except IntegrityError as exc:
            raise HTTPException(status_code=409, detail="등록 중 데이터가 변경되었습니다. 미리보기 후 다시 시도해주세요.") from exc
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail="접수 데이터를 등록하지 못했습니다. 잠시 후 다시 시도해주세요.") from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail="접수 데이터를 등록하지 못했습니다.") from exc

        record_audit_log(
            db, request, current_user,
            action_type="excel_import",
            menu_key="dashboard",
            menu_name="온라인 TEAM > 리콜 관리",
            target_type="recall_application_upload",
            target_id=result.batch_id,
            target_name="접수 데이터 Excel 등록",
            action_summary="리콜 접수 데이터 Excel 등록: 신규 {}건, 중복 {}건, 제외 {}건".format(
                result.registered, result.duplicate, result.rejected
            ),
            after_data={
                "batch_id": result.batch_id,
                "registered_count": result.registered,
                "duplicate_count": result.duplicate,
                "rejected_count": result.rejected,
            },
        )
        return jsonable_encoder(asdict(result))
    finally:
        await file.close()


@router.get("/summary")
def read_recall_application_summary(
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    return get_recall_summary(db)


@router.get("")
def read_recall_applications(
    keyword: Optional[str] = Query(None, max_length=100),
    status: Optional[str] = Query(None, max_length=40),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    result = list_recall_applications(db, keyword=keyword, status=status, page=page, page_size=page_size)
    return jsonable_encoder({
        **{key: value for key, value in result.items() if key != "items"},
        "items": [
            {
                "id": item.id,
                "application_date": item.application_date,
                "quantity": item.quantity,
                "customer_name": item.customer_name,
                "phone_original": item.phone_original,
                "phone_normalized": item.phone_normalized,
                "address": item.address,
                "memo": item.memo,
                "serial_number": item.serial_number,
                "lot_number": item.lot_number,
                "pickup_agreement": item.pickup_agreement,
                "pickup_date": item.pickup_date,
                "replacement_shipping_agreement": item.replacement_shipping_agreement,
                "current_status": item.current_status,
                "created_at": item.created_at,
            }
            for item in result["items"]
        ],
    })


@router.get("/{application_id}")
def read_recall_application_detail(
    application_id: int,
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    detail = get_recall_application_detail(db, application_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="리콜 접수 데이터를 찾을 수 없습니다.")
    return jsonable_encoder(detail)


@router.patch("/{application_id}/status")
def update_recall_application_status(
    application_id: int,
    payload: RecallStatusChangeRequest,
    request: Request,
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        result = change_recall_application_status(
            db, application_id=application_id, status=payload.status,
            reason=payload.reason, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="상태를 변경하지 못했습니다. 잠시 후 다시 시도해주세요.") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="리콜 접수 데이터를 찾을 수 없습니다.")

    if result["changed"]:
        record_audit_log(
            db, request, current_user,
            action_type="update",
            menu_key="online_recall",
            menu_name="온라인 TEAM > 리콜 관리",
            target_type="recall_application",
            target_id=application_id,
            target_name="리콜 상태 변경",
            action_summary="리콜 상태 변경: application_id={} {} → {} user_id={}".format(
                application_id, result["previous_status"], payload.status, current_user.id
            ),
            before_data={"current_status": result["previous_status"]},
            after_data={"current_status": payload.status},
        )
    detail = get_recall_application_detail(db, application_id)
    return jsonable_encoder({"changed": result["changed"], "application": detail})
