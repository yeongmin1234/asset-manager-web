from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from uuid import uuid4

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.beverage_order_record import BeverageOrderRecord
from app.schemas.beverage_order_record import BeverageOrderRecordRead, BeverageOrderSummary
from app.services.activity_log_service import (
    record_beverage_order_activity,
    serialize_beverage_order_activity_data,
)


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024
BEVERAGE_UPLOAD_SUBDIR = "beverage-orders"


class BeverageOrderRecordNotFoundError(Exception):
    pass


class BeverageOrderImageError(Exception):
    pass


def get_beverage_order_records(
    db: Session,
    *,
    order_month: Optional[str] = None,
    order_type: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[BeverageOrderRecord]:
    statement = select(BeverageOrderRecord)
    if order_month:
        statement = statement.where(BeverageOrderRecord.order_month == order_month)
    if order_type:
        statement = statement.where(BeverageOrderRecord.order_type == normalize_order_type(order_type))
    if keyword:
        keyword_pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                BeverageOrderRecord.title.ilike(keyword_pattern),
                BeverageOrderRecord.memo.ilike(keyword_pattern),
                BeverageOrderRecord.image_original_name.ilike(keyword_pattern),
            )
        )
    statement = statement.order_by(
        BeverageOrderRecord.created_at.desc(),
        BeverageOrderRecord.id.desc(),
    )
    return list(db.scalars(statement).all())


def create_beverage_order_record(
    db: Session,
    *,
    image_path: str,
    image_original_name: str,
    order_type: str = "beverage",
    memo: Optional[str] = None,
    total_amount: Optional[int] = None,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeverageOrderRecord:
    today = date.today()
    record = BeverageOrderRecord(
        order_date=today,
        order_month=today.strftime("%Y-%m"),
        title=f"{today.isoformat()} 음료 주문",
        order_type=normalize_order_type(order_type),
        image_path=image_path,
        image_original_name=image_original_name,
        memo=normalize_optional_text(memo),
        total_amount=total_amount,
    )
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
    *,
    memo: Optional[str] = None,
    order_type: str = "beverage",
    total_amount: Optional[int] = None,
    image_path: Optional[str] = None,
    image_original_name: Optional[str] = None,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BeverageOrderRecord:
    record = get_beverage_order_record(db, order_id)
    before_data = serialize_beverage_order_activity_data(record)
    old_image_path = record.image_path
    record.order_type = normalize_order_type(order_type)
    record.memo = normalize_optional_text(memo)
    record.total_amount = total_amount
    if image_path:
        record.image_path = image_path
        record.image_original_name = image_original_name
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
    if image_path and old_image_path and old_image_path != image_path:
        delete_beverage_image_file(old_image_path)
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
    image_path = record.image_path
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
    if image_path:
        delete_beverage_image_file(image_path)
    return deleted_record


def get_beverage_order_summary(db: Session) -> BeverageOrderSummary:
    current_month = date.today().strftime("%Y-%m")
    this_month_condition = BeverageOrderRecord.order_month == current_month
    row = db.execute(
        select(
            func.count(BeverageOrderRecord.id).label("total"),
            func.coalesce(func.sum(case((this_month_condition, 1), else_=0)), 0).label(
                "this_month"
            ),
            func.coalesce(func.sum(BeverageOrderRecord.total_amount), 0).label(
                "total_amount_total"
            ),
            func.coalesce(
                func.sum(case((this_month_condition, BeverageOrderRecord.total_amount), else_=0)),
                0,
            ).label("this_month_amount"),
            func.coalesce(
                func.sum(case((BeverageOrderRecord.order_type == "beverage", 1), else_=0)),
                0,
            ).label("beverage"),
            func.coalesce(
                func.sum(case((BeverageOrderRecord.order_type == "supplies", 1), else_=0)),
                0,
            ).label("supplies"),
        )
    ).one()
    return BeverageOrderSummary(
        total=int(row.total or 0),
        this_month=int(row.this_month or 0),
        total_amount_total=int(row.total_amount_total or 0),
        this_month_amount=int(row.this_month_amount or 0),
        beverage=int(row.beverage or 0),
        supplies=int(row.supplies or 0),
    )


def save_beverage_image_file(
    *,
    original_filename: Optional[str],
    content: bytes,
) -> Tuple[str, str]:
    if not content:
        raise BeverageOrderImageError("이미지 파일을 첨부해주세요.")
    if len(content) > MAX_IMAGE_SIZE_BYTES:
        raise BeverageOrderImageError("이미지 파일은 10MB 이하만 업로드할 수 있습니다.")

    original_name = Path(original_filename or "beverage-order.png").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise BeverageOrderImageError("jpg, jpeg, png, webp 이미지만 업로드할 수 있습니다.")

    upload_dir = get_beverage_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex}{extension}"
    stored_path = upload_dir / stored_name
    try:
        stored_path.write_bytes(content)
    except OSError as exc:
        raise BeverageOrderImageError("이미지 저장에 실패했습니다.") from exc
    return f"{BEVERAGE_UPLOAD_SUBDIR}/{stored_name}", original_name


def delete_beverage_image_file(image_path: str) -> None:
    try:
        target = Path(settings.upload_dir).resolve() / image_path
        upload_root = Path(settings.upload_dir).resolve()
        if upload_root not in target.parents:
            return
        if target.exists():
            target.unlink()
    except OSError:
        return


def get_beverage_upload_dir() -> Path:
    return Path(settings.upload_dir).resolve() / BEVERAGE_UPLOAD_SUBDIR


def normalize_optional_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized_value = value.strip()
    return normalized_value or None


def normalize_order_type(value: Optional[str]) -> str:
    normalized_value = (value or "beverage").strip() or "beverage"
    if normalized_value not in {"beverage", "supplies"}:
        return "beverage"
    return normalized_value


def format_beverage_order_target_name(record: BeverageOrderRecord) -> str:
    return record.title or f"음료주문기록 #{record.id}"
