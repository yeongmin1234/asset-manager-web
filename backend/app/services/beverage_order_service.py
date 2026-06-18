from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.beverage_order_record import BeverageOrderRecord
from app.schemas.beverage_order_record import (
    BeverageOrderRecordCreate,
    BeverageOrderRecordRead,
    BeverageOrderRecordUpdate,
    BeverageOrderSummary,
)
from app.services.activity_log_service import (
    record_beverage_order_activity,
    serialize_beverage_order_activity_data,
)


class BeverageOrderRecordNotFoundError(Exception):
    pass


def get_beverage_order_records(
    db: Session,
    *,
    order_month: Optional[str] = None,
    vendor: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[BeverageOrderRecord]:
    statement = select(BeverageOrderRecord)
    if order_month:
        statement = statement.where(BeverageOrderRecord.order_month == order_month)
    if vendor:
        statement = statement.where(BeverageOrderRecord.vendor == vendor)
    if keyword:
        keyword_pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                BeverageOrderRecord.title.ilike(keyword_pattern),
                BeverageOrderRecord.items_summary.ilike(keyword_pattern),
                BeverageOrderRecord.requester.ilike(keyword_pattern),
                BeverageOrderRecord.memo.ilike(keyword_pattern),
            )
        )
    statement = statement.order_by(
        BeverageOrderRecord.order_date.desc().nullslast(),
        BeverageOrderRecord.created_at.desc(),
        BeverageOrderRecord.id.desc(),
    )
    return list(db.scalars(statement).all())


def create_beverage_order_record(
    db: Session,
    payload: BeverageOrderRecordCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeverageOrderRecord:
    record = BeverageOrderRecord(**normalize_payload(payload.model_dump()))
    db.add(record)
    db.flush()
    record_beverage_order_activity(
        db,
        action_type="create",
        target_id=record.id,
        target_name=format_beverage_order_target_name(record),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[음료주문기록] 등록: {format_beverage_order_target_name(record)}",
        after_data=serialize_beverage_order_activity_data(record),
    )
    db.commit()
    db.refresh(record)
    return record


def get_beverage_order_record(
    db: Session,
    order_id: int,
) -> BeverageOrderRecord:
    record = db.scalar(select(BeverageOrderRecord).where(BeverageOrderRecord.id == order_id))
    if record is None:
        raise BeverageOrderRecordNotFoundError(f"Beverage order record not found: {order_id}")
    return record


def update_beverage_order_record(
    db: Session,
    order_id: int,
    payload: BeverageOrderRecordUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeverageOrderRecord:
    record = get_beverage_order_record(db, order_id)
    before_data = serialize_beverage_order_activity_data(record)
    for field_name, value in normalize_payload(payload.model_dump()).items():
        setattr(record, field_name, value)
    record.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_beverage_order_activity(
        db,
        action_type="update",
        target_id=record.id,
        target_name=format_beverage_order_target_name(record),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[음료주문기록] 수정: {format_beverage_order_target_name(record)}",
        before_data=before_data,
        after_data=serialize_beverage_order_activity_data(record),
    )
    db.commit()
    db.refresh(record)
    return record


def delete_beverage_order_record(
    db: Session,
    order_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeverageOrderRecordRead:
    record = get_beverage_order_record(db, order_id)
    before_data = serialize_beverage_order_activity_data(record)
    target_name = format_beverage_order_target_name(record)
    deleted_record = BeverageOrderRecordRead.model_validate(record)
    record_beverage_order_activity(
        db,
        action_type="delete",
        target_id=record.id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[음료주문기록] 삭제: {target_name}",
        before_data=before_data,
    )
    db.delete(record)
    db.commit()
    return deleted_record


def get_beverage_order_summary(db: Session) -> BeverageOrderSummary:
    current_month = date.today().strftime("%Y-%m")
    this_month_condition = BeverageOrderRecord.order_month == current_month
    row = db.execute(
        select(
            func.count(BeverageOrderRecord.id).label("total"),
            func.coalesce(
                func.sum(case((this_month_condition, 1), else_=0)),
                0,
            ).label("this_month"),
            func.coalesce(func.sum(BeverageOrderRecord.total_amount), 0).label("total_amount"),
            func.coalesce(
                func.sum(case((this_month_condition, BeverageOrderRecord.total_amount), else_=0)),
                0,
            ).label("this_month_amount"),
        )
    ).one()
    return BeverageOrderSummary(
        total=int(row.total or 0),
        this_month=int(row.this_month or 0),
        total_amount=int(row.total_amount or 0),
        this_month_amount=int(row.this_month_amount or 0),
    )


def normalize_payload(data: Dict[str, object]) -> Dict[str, object]:
    order_date = data.get("order_date")
    order_month = data.get("order_month")
    if not order_month and isinstance(order_date, date):
        data["order_month"] = order_date.strftime("%Y-%m")
    return data


def format_beverage_order_target_name(record: BeverageOrderRecord) -> str:
    return record.title or f"음료주문기록 #{record.id}"
