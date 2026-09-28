"""Database workflow for registering and reading recall application Excel rows."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.models.recall_application import (
    APPLICATION_RECEIVED,
    REVIEW_REQUIRED,
    STOPPED,
    RecallApplication,
    RecallApplicationUploadBatch,
    RecallStatusHistory,
)
from app.models.user import User
from app.services.recall_application_excel import preview_recall_applications


@dataclass(frozen=True)
class CommitResult:
    batch_id: int
    registered: int
    duplicate: int
    rejected: int
    unselected_review: int
    rows: tuple


def existing_application_records(db: Session) -> List[Dict[str, Any]]:
    return [
        {
            "id": row.id,
            "status": row.current_status,
            "serial_number": row.serial_number,
            "phone_original": row.phone_original,
            "phone_normalized": row.phone_normalized,
        }
        for row in db.scalars(select(RecallApplication)).all()
    ]


def commit_recall_applications(
    db: Session,
    *,
    file_bytes: bytes,
    source_filename: str,
    selected_row_numbers: Sequence[int],
    user_id: int,
) -> CommitResult:
    selected = set(selected_row_numbers)
    if not selected or len(selected) != len(selected_row_numbers) or any(not isinstance(value, int) or value < 1 for value in selected):
        raise ValueError("등록할 행을 하나 이상 올바르게 선택해주세요.")

    # Registration requests are serialized on PostgreSQL so two concurrent files
    # cannot both pass the same serial/phone check before either transaction commits.
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(
            "LOCK TABLE recall_application_upload_batches, recall_applications "
            "IN SHARE ROW EXCLUSIVE MODE"
        ))

    source_sha256 = hashlib.sha256(file_bytes).hexdigest()
    batch = db.scalar(
        select(RecallApplicationUploadBatch).where(RecallApplicationUploadBatch.source_sha256 == source_sha256)
    )
    existing_batch_rows = set()
    if batch is not None:
        existing_batch_rows = set(db.scalars(
            select(RecallApplication.source_row_number).where(RecallApplication.upload_batch_id == batch.id)
        ).all())

    preview = preview_recall_applications(
        file_bytes,
        source_filename=source_filename,
        existing_records=existing_application_records(db),
    )
    parsed_by_number = {row.raw_row_number: row for row in preview.rows}
    unknown = selected - set(parsed_by_number)
    if unknown:
        raise ValueError("선택한 행이 현재 Excel 파일에 없습니다.")

    counts = preview.counts()
    registered = duplicate = rejected = 0
    results = []
    try:
        if batch is None:
            batch = RecallApplicationUploadBatch(
                source_filename=source_filename[:255],
                source_sha256=source_sha256,
                total_rows=len(preview.rows),
                valid_count=counts["valid"],
                review_count=counts["review"],
                duplicate_count=counts["duplicate"],
                error_count=counts["error"],
                excluded_count=counts["blank"] + counts["instruction"],
                registered_count=0,
                uploaded_by=user_id,
            )
            db.add(batch)
            db.flush()

        for row_number in sorted(selected):
            row = parsed_by_number[row_number]
            if row_number in existing_batch_rows:
                duplicate += 1
                results.append({"row_number": row_number, "result": "ALREADY_REGISTERED"})
                continue
            if row.status == "duplicate":
                duplicate += 1
                duplicate_code = next(
                    (issue.code for issue in row.issues if issue.code == "DUPLICATE_SERIAL"),
                    next((issue.code for issue in row.issues if issue.code == "DUPLICATE_PHONE"), "DUPLICATE"),
                )
                results.append({"row_number": row_number, "result": duplicate_code})
                continue
            if row.status not in {"valid", "review"}:
                rejected += 1
                code = row.issues[0].code if row.issues else "EXCLUDED"
                results.append({"row_number": row_number, "result": code})
                continue

            data = row.data
            application = RecallApplication(
                upload_batch_id=batch.id,
                source_row_number=row_number,
                application_date=data.get("application_date"),
                quantity=data.get("quantity"),
                customer_name=data["customer_name"],
                phone_original=data["phone_original"],
                phone_normalized=data["phone_normalized"],
                address=data["address"],
                memo=data.get("memo"),
                serial_number=data.get("serial_number"),
                lot_number=data.get("lot_number"),
                pickup_agreement=data.get("pickup_agreement"),
                pickup_date=data.get("pickup_date"),
                replacement_shipping_agreement=data.get("replacement_shipping_agreement"),
                current_status=APPLICATION_RECEIVED,
                created_by=user_id,
            )
            db.add(application)
            db.flush()
            db.add(RecallStatusHistory(
                recall_application_id=application.id,
                previous_status=None,
                new_status=APPLICATION_RECEIVED,
                changed_by=user_id,
                change_type="EXCEL_REGISTRATION",
                reason="접수 데이터 Excel 등록",
            ))
            registered += 1
            results.append({"row_number": row_number, "result": "REGISTERED", "application_id": application.id})

        batch.registered_count = int(batch.registered_count or 0) + registered
        batch_id = batch.id
        db.commit()
    except Exception:
        db.rollback()
        raise

    unselected_review = sum(
        1 for row in preview.rows if row.status == "review" and row.raw_row_number not in selected
    )
    return CommitResult(batch_id, registered, duplicate, rejected, unselected_review, tuple(results))


def list_recall_applications(
    db: Session,
    *,
    keyword: Optional[str],
    status: Optional[str],
    page: int,
    page_size: int,
) -> dict:
    conditions = []
    if keyword and keyword.strip():
        search_text = keyword.strip()
        pattern = "%{}%".format(search_text)
        phone_search = re.sub(r"[\s-]", "", search_text)
        phone_conditions = [RecallApplication.phone_normalized.ilike(pattern)]
        if phone_search != search_text and phone_search.isdigit():
            phone_conditions.append(RecallApplication.phone_normalized.ilike("%{}%".format(phone_search)))
        conditions.append(or_(
            RecallApplication.customer_name.ilike(pattern),
            RecallApplication.phone_original.ilike(pattern),
            *phone_conditions,
            RecallApplication.serial_number.ilike(pattern),
        ))
    if status:
        conditions.append(RecallApplication.current_status == status)

    query = select(RecallApplication).where(*conditions)
    total = int(db.scalar(select(func.count()).select_from(query.subquery())) or 0)
    items = list(db.scalars(
        query.order_by(RecallApplication.created_at.desc(), RecallApplication.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all())
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, int(math.ceil(total / float(page_size)))),
    }


def get_recall_summary(db: Session) -> dict:
    received = int(db.scalar(
        select(func.count()).select_from(RecallApplication).where(
            RecallApplication.current_status == APPLICATION_RECEIVED
        )
    ) or 0)
    return {"total": 0, "received": received, "orders": 0, "shipped": 0}


MANUAL_STATUSES = (APPLICATION_RECEIVED, REVIEW_REQUIRED, STOPPED)


def get_recall_application_detail(db: Session, application_id: int) -> Optional[dict]:
    application = db.get(RecallApplication, application_id)
    if application is None:
        return None
    batch = db.get(RecallApplicationUploadBatch, application.upload_batch_id)
    history = list(db.scalars(
        select(RecallStatusHistory)
        .where(RecallStatusHistory.recall_application_id == application_id)
        .order_by(RecallStatusHistory.changed_at.desc(), RecallStatusHistory.id.desc())
    ).all())
    user_ids = {application.created_by}
    user_ids.update(item.changed_by for item in history)
    names = {
        user.id: user.name for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }
    return {
        "id": application.id,
        "application_date": application.application_date,
        "quantity": application.quantity,
        "customer_name": application.customer_name,
        "phone_original": application.phone_original,
        "phone_normalized": application.phone_normalized,
        "address": application.address,
        "memo": application.memo,
        "serial_number": application.serial_number,
        "lot_number": application.lot_number,
        "pickup_agreement": application.pickup_agreement,
        "pickup_date": application.pickup_date,
        "replacement_shipping_agreement": application.replacement_shipping_agreement,
        "current_status": application.current_status,
        "created_at": application.created_at,
        "created_by": application.created_by,
        "created_by_name": names.get(application.created_by),
        "upload_batch": {
            "id": batch.id,
            "source_filename": batch.source_filename,
            "uploaded_at": batch.uploaded_at,
        } if batch is not None else None,
        "status_history": [
            {
                "id": item.id,
                "previous_status": item.previous_status,
                "new_status": item.new_status,
                "changed_at": item.changed_at,
                "changed_by": item.changed_by,
                "changed_by_name": names.get(item.changed_by),
                "change_type": item.change_type,
                "reason": item.reason,
            }
            for item in history
        ],
    }


def change_recall_application_status(
    db: Session, *, application_id: int, status: str, reason: str, user_id: int
) -> Optional[dict]:
    if status not in MANUAL_STATUSES:
        raise ValueError("변경할 수 없는 상태입니다.")
    cleaned_reason = reason.strip()
    if not cleaned_reason:
        raise ValueError("상태 변경 사유를 입력해주세요.")
    if len(cleaned_reason) > 255:
        raise ValueError("상태 변경 사유는 255자 이내로 입력해주세요.")

    try:
        application = db.scalar(
            select(RecallApplication).where(RecallApplication.id == application_id).with_for_update()
        )
        if application is None:
            return None
        previous_status = application.current_status
        if previous_status == status:
            db.rollback()
            return {"changed": False, "previous_status": previous_status}

        application.current_status = status
        db.add(RecallStatusHistory(
            recall_application_id=application_id,
            previous_status=previous_status,
            new_status=status,
            changed_by=user_id,
            change_type="MANUAL",
            reason=cleaned_reason,
        ))
        db.commit()
        return {"changed": True, "previous_status": previous_status}
    except Exception:
        db.rollback()
        raise
