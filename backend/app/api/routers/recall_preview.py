"""Preview, register, and read APIs for online TEAM recall applications."""

import json
from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import RecallApplication
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
    bulk_change_recall_applications,
    resolve_recall_duplicate,
)
from app.services.recall_order_service import (
    confirm_order, export_orders, get_order_batch_workbook, list_orders,
    order_summary, preview_orders,
)


router = APIRouter(prefix="/online/recall/applications", tags=["online-recall"])
MAX_PREVIEW_FILE_SIZE = 5 * 1024 * 1024


class RecallStatusChangeRequest(BaseModel):
    status: str
    reason: str


class RecallBulkStatusChangeRequest(BaseModel):
    ids: List[int]
    status: str
    reason: str


class RecallOrderSelectionRequest(BaseModel):
    ids: List[int]


class RecallDuplicateResolutionRequest(BaseModel):
    action: str
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
            action_summary="리콜 접수 데이터 Excel 등록: 신규 {}건, 중복 확인 {}건, 제외 {}건".format(
                result.registered, result.duplicate, result.rejected
            ),
            after_data={
                "batch_id": result.batch_id,
                "registered_count": result.registered,
                "duplicate_count": result.duplicate,
                "rejected_count": result.rejected,
                "review_count": result.review,
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
    duplicate_only: bool = Query(False),
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    result = list_recall_applications(db, keyword=keyword, status=status, page=page,
                                      page_size=page_size, duplicate_only=duplicate_only)
    references = {
        reference_id: db.get(RecallApplication, reference_id)
        for reference_id in {item.duplicate_reference_id for item in result["items"] if item.duplicate_reference_id}
    }
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
                "duplicate_flag": item.duplicate_flag,
                "duplicate_reason": item.duplicate_reason,
                "duplicate_reference_id": item.duplicate_reference_id,
                "duplicate_resolution": item.duplicate_resolution,
                "duplicate_resolved_at": item.duplicate_resolved_at,
                "source_row_number": item.source_row_number,
                "duplicate_reference": {
                    "id": references[item.duplicate_reference_id].id,
                    "application_date": references[item.duplicate_reference_id].application_date,
                    "customer_name": references[item.duplicate_reference_id].customer_name,
                    "phone_original": references[item.duplicate_reference_id].phone_original,
                    "serial_number": references[item.duplicate_reference_id].serial_number,
                } if item.duplicate_reference_id and references.get(item.duplicate_reference_id) else None,
                "created_at": item.created_at,
            }
            for item in result["items"]
        ],
    })


@router.patch("/duplicates/{application_id}/resolve")
def resolve_recall_duplicate_api(
    application_id: int,
    payload: RecallDuplicateResolutionRequest,
    request: Request,
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        result = resolve_recall_duplicate(db, application_id=application_id, action=payload.action,
                                          reason=payload.reason, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="중복 확인 처리에 실패했습니다.") from exc
    record_audit_log(
        db, request, current_user, action_type="update", menu_key="online_recall",
        menu_name="온라인 TEAM > 리콜 관리", target_type="recall_duplicate",
        target_id=application_id, target_name="중복 확인 처리",
        action_summary="리콜 중복 확인 처리: application_id={} action={} user_id={}".format(
            application_id, payload.action, current_user.id),
        before_data={"duplicate_flag": True},
        after_data={"duplicate_flag": result["duplicate_flag"], "duplicate_resolution": payload.action,
                    "reason": payload.reason},
    )
    return result


@router.patch("/bulk-status")
def update_recall_applications_bulk_status(
    payload: RecallBulkStatusChangeRequest,
    request: Request,
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        result = bulk_change_recall_applications(
            db, ids=payload.ids, status=payload.status,
            reason=payload.reason, user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="일괄 상태를 변경하지 못했습니다. 잠시 후 다시 시도해주세요.") from exc

    record_audit_log(
        db, request, current_user,
        action_type="update",
        menu_key="online_recall",
        menu_name="온라인 TEAM > 리콜 관리",
        target_type="recall_application_bulk",
        target_id=None,
        target_name="리콜 일괄 상태 변경",
        action_summary="리콜 일괄 상태 변경: 상태 {}, 요청 {}건, 성공 {}건, user_id={}".format(
            payload.status, result["requested"], result["updated"], current_user.id
        ),
        after_data={"status": payload.status, **{key: result[key] for key in ("requested", "updated", "skipped", "failed")}},
    )
    return result


@router.get("/orders/summary")
def read_recall_order_summary(
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    return order_summary(db)


@router.get("/orders")
def read_recall_orders(
    status: str = Query("", max_length=40),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=100),
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        return jsonable_encoder(list_orders(db, status=status, page=page, page_size=page_size))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/preview")
def preview_recall_orders(
    payload: RecallOrderSelectionRequest,
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        return jsonable_encoder(preview_orders(db, payload.ids))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/orders/export")
def export_recall_orders(
    payload: RecallOrderSelectionRequest,
    request: Request,
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        result = export_orders(db, ids=payload.ids, user_id=current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="SCM Excel을 생성하지 못했습니다.") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="SCM Excel을 생성하지 못했습니다.") from exc
    record_audit_log(
        db, request, current_user,
        action_type="export", menu_key="online_recall", menu_name="온라인 TEAM > 리콜 관리",
        target_type="recall_order_batch", target_id=result["batch_id"], target_name="SCM 발주 Excel 생성",
        action_summary="SCM 발주 Excel 생성: batch_id={} 건수={} 수량={} user_id={}".format(
            result["batch_id"], result["item_count"], result["total_quantity"], current_user.id,
        ),
        after_data={key: result[key] for key in ("batch_id", "item_count", "total_quantity")},
    )
    return Response(
        content=result["content"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(result["file_name"]), "Cache-Control": "no-store"},
    )


@router.get("/orders/batches/{batch_id}/download")
def download_recall_order_batch(
    batch_id: int,
    _user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    try:
        result = get_order_batch_workbook(db, batch_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=result["content"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="{}"'.format(result["file_name"]), "Cache-Control": "no-store"},
    )


@router.patch("/orders/{application_id}/confirm")
def confirm_recall_order(
    application_id: int,
    request: Request,
    current_user: User = Depends(require_recall_preview_access),
    db: Session = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 발주 완료로 처리할 수 있습니다.")
    try:
        result = confirm_order(db, application_id=application_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="발주 완료 처리에 실패했습니다.") from exc
    record_audit_log(
        db, request, current_user,
        action_type="update", menu_key="online_recall", menu_name="온라인 TEAM > 리콜 관리",
        target_type="recall_order", target_id=application_id, target_name="SCM 발주 완료",
        action_summary="SCM 발주 완료: application_id={} batch_id={} user_id={}".format(
            application_id, result["order_batch_id"], current_user.id,
        ),
        before_data={"order_status": "ORDER_EXPORTED"},
        after_data={"order_status": result["order_status"]},
    )
    return result


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
