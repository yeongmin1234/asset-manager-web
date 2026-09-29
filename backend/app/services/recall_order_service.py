"""Order tracking for SCM recall exports, separate from recall status."""

import math
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.recall_application import (
    IN_PROGRESS, ORDER_CONFIRMED, ORDER_EXPORTED, ORDER_PENDING,
    RecallApplication, RecallOrderBatch,
)
from app.services.recall_order_excel import SCM_HEADERS, build_scm_workbook, scm_row


def _eligible_pending():
    return (
        RecallApplication.current_status == IN_PROGRESS,
        RecallApplication.replacement_shipping_agreement == "동의",
        RecallApplication.order_status == ORDER_PENDING,
    )


def order_summary(db: Session) -> Dict[str, int]:
    return {
        "pending_count": int(db.scalar(select(func.count()).select_from(RecallApplication).where(*_eligible_pending())) or 0),
        "exported_count": int(db.scalar(select(func.count()).select_from(RecallApplication).where(RecallApplication.order_status == ORDER_EXPORTED)) or 0),
        "confirmed_count": int(db.scalar(select(func.count()).select_from(RecallApplication).where(RecallApplication.order_status == ORDER_CONFIRMED)) or 0),
    }


def list_orders(db: Session, *, status: str, page: int, page_size: int) -> Dict[str, object]:
    if status not in ("", ORDER_PENDING, ORDER_EXPORTED, ORDER_CONFIRMED):
        raise ValueError("주문 상태 필터가 올바르지 않습니다.")
    visible = or_(
        and_(*_eligible_pending()),
        RecallApplication.order_status.in_((ORDER_EXPORTED, ORDER_CONFIRMED)),
    )
    query = select(RecallApplication).where(visible)
    if status:
        query = query.where(RecallApplication.order_status == status)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    items = list(db.scalars(
        query.order_by(RecallApplication.created_at.desc(), RecallApplication.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all())
    return {
        "items": [_order_item(application) for application in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, int(math.ceil(total / float(page_size)))),
    }


def _order_item(application: RecallApplication) -> Dict[str, object]:
    return {
        "id": application.id,
        "application_date": application.application_date,
        "customer_name": application.customer_name,
        "phone_original": application.phone_original,
        "address": application.address,
        "quantity": application.quantity,
        "memo": application.memo,
        "current_status": application.current_status,
        "order_status": application.order_status,
        "order_batch_id": application.order_batch_id,
        "order_exported_at": application.order_exported_at,
        "order_confirmed_at": application.order_confirmed_at,
    }


def _selected_pending(db: Session, ids: Sequence[int], *, lock: bool) -> List[RecallApplication]:
    if not ids or len(ids) > 100 or any(type(value) is not int or value < 1 for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("발주 대상을 1~100건 중복 없이 선택해주세요.")
    statement = select(RecallApplication).where(RecallApplication.id.in_(ids)).order_by(RecallApplication.id)
    if lock:
        statement = statement.with_for_update()
    applications = list(db.scalars(statement).all())
    if len(applications) != len(ids):
        raise ValueError("선택한 발주 대상을 찾을 수 없습니다.")
    by_id = {application.id: application for application in applications}
    selected = [by_id[application_id] for application_id in ids]
    for application in selected:
        if (application.current_status != IN_PROGRESS or
                application.replacement_shipping_agreement != "동의" or
                application.order_status != ORDER_PENDING):
            raise ValueError("진행중·출고 동의·발주 대기 상태의 건만 Excel로 생성할 수 있습니다.")
        if type(application.quantity) is not int or application.quantity < 1:
            raise ValueError("선택한 건의 주문수량을 확인해주세요.")
    return selected


def preview_orders(db: Session, ids: Sequence[int]) -> Dict[str, object]:
    selected = _selected_pending(db, ids, lock=False)
    return {
        "ids": list(ids),
        "item_count": len(selected),
        "total_quantity": sum(application.quantity for application in selected),
        "columns": list(SCM_HEADERS),
        "rows": [scm_row(application) for application in selected],
    }


def export_orders(db: Session, *, ids: Sequence[int], user_id: int) -> Dict[str, object]:
    try:
        selected = _selected_pending(db, ids, lock=True)
        rows = [scm_row(application) for application in selected]
        workbook_bytes = build_scm_workbook(rows)
        total_quantity = sum(application.quantity for application in selected)
        batch = RecallOrderBatch(
            file_name="pending.xlsx", item_count=len(selected),
            total_quantity=total_quantity, file_content=workbook_bytes, created_by=user_id,
        )
        db.add(batch)
        db.flush()
        batch.file_name = "recall_scm_orders_{}_{}.xlsx".format(datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S"), batch.id)
        now = datetime.now(timezone.utc)
        for application in selected:
            application.order_status = ORDER_EXPORTED
            application.order_exported_at = now
            application.order_batch_id = batch.id
        result = {
            "batch_id": batch.id, "file_name": batch.file_name, "item_count": len(selected),
            "total_quantity": total_quantity, "content": workbook_bytes,
        }
        db.commit()
        return result
    except Exception:
        db.rollback()
        raise


def get_order_batch_workbook(db: Session, batch_id: int) -> Dict[str, object]:
    batch = db.get(RecallOrderBatch, batch_id)
    if batch is None:
        raise LookupError("SCM Excel 생성 이력을 찾을 수 없습니다.")
    return {"file_name": batch.file_name, "content": batch.file_content}


def confirm_order(db: Session, *, application_id: int) -> Dict[str, object]:
    try:
        application = db.scalar(select(RecallApplication).where(RecallApplication.id == application_id).with_for_update())
        if application is None:
            raise LookupError("리콜 발주 대상을 찾을 수 없습니다.")
        if application.order_status != ORDER_EXPORTED:
            raise ValueError("Excel 생성 완료 상태에서만 발주 완료로 변경할 수 있습니다.")
        application.order_status = ORDER_CONFIRMED
        application.order_confirmed_at = datetime.now(timezone.utc)
        db.commit()
        return {"id": application.id, "order_status": application.order_status, "order_batch_id": application.order_batch_id}
    except Exception:
        db.rollback()
        raise
