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
    IN_PROGRESS,
    REVIEW_REQUIRED,
    STOPPED,
    SHIPPED,
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
    status_counts = {
        status: int(count) for status, count in db.execute(
            select(RecallApplication.current_status, func.count())
            .group_by(RecallApplication.current_status)
        ).all()
    }
    received_count = sum(status_counts.values())
    return {
        "total_count": _get_total_target_count(received_count),
        "received_count": received_count,
        "remaining_count": status_counts.get(APPLICATION_RECEIVED, 0),
        "in_progress_count": status_counts.get(IN_PROGRESS, 0),
        "shipped_count": status_counts.get(SHIPPED, 0),
    }


def _get_total_target_count(registered_application_count: int) -> int:
    # Until recall Raw Data has its own source, every registered application is a target.
    return registered_application_count


MANUAL_STATUSES = (APPLICATION_RECEIVED, IN_PROGRESS, REVIEW_REQUIRED, STOPPED)


def bulk_ship_recall_applications(
    db: Session, *, ids: Sequence[int], status: str, reason: str, user_id: int
) -> dict:
    if status != SHIPPED:
        raise ValueError("일괄 변경은 발송 완료 상태만 지원합니다.")
    if not ids or len(ids) > 100 or any(type(value) is not int or value < 1 for value in ids):
        raise ValueError("처리할 ID를 1~100개 선택해주세요.")
    if len(set(ids)) != len(ids):
        raise ValueError("중복된 ID가 포함되어 있습니다.")
    cleaned_reason = reason.strip()
    if not cleaned_reason or len(cleaned_reason) > 255:
        raise ValueError("변경 사유는 1~255자로 입력해주세요.")

    try:
        applications = {
            application.id: application for application in db.scalars(
                select(RecallApplication).where(RecallApplication.id.in_(ids))
                .order_by(RecallApplication.id).with_for_update()
            ).all()
        }
        results = []
        updated = skipped = failed = 0
        for application_id in ids:
            application = applications.get(application_id)
            if application is None:
                failed += 1
                results.append({"id": application_id, "result": "FAILED", "reason_code": "NOT_FOUND"})
            elif application.current_status == SHIPPED:
                skipped += 1
                results.append({"id": application_id, "result": "SKIPPED", "reason_code": "ALREADY_SHIPPED"})
            elif application.current_status not in (APPLICATION_RECEIVED, IN_PROGRESS):
                failed += 1
                results.append({"id": application_id, "result": "FAILED", "reason_code": "INVALID_CURRENT_STATUS"})
            else:
                previous_status = application.current_status
                application.current_status = SHIPPED
                db.add(RecallStatusHistory(
                    recall_application_id=application_id,
                    previous_status=previous_status,
                    new_status=SHIPPED,
                    changed_by=user_id,
                    change_type="BULK",
                    reason=cleaned_reason,
                ))
                updated += 1
                results.append({"id": application_id, "result": "UPDATED", "reason_code": None})
        if updated:
            db.commit()
        else:
            db.rollback()
        return {"requested": len(ids), "updated": updated, "skipped": skipped, "failed": failed, "results": results}
    except Exception:
        db.rollback()
        raise


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
