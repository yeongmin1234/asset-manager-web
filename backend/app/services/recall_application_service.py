"""Database workflow for registering and reading recall application Excel rows."""

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
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
    RecallDuplicateResolutionHistory,
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
    normal: int = 0
    review: int = 0
    already_registered: int = 0


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
    registered = duplicate = rejected = normal = review = already_registered = 0
    results = []
    registered_by_row = {}
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
                already_registered += 1
                results.append({"row_number": row_number, "result": "ALREADY_REGISTERED"})
                continue
            if row.status not in {"valid", "review", "duplicate"}:
                rejected += 1
                code = row.issues[0].code if row.issues else "EXCLUDED"
                results.append({"row_number": row_number, "result": code})
                continue

            data = row.data
            duplicate_issues = [issue for issue in row.issues if issue.code in {"DUPLICATE_PHONE", "DUPLICATE_SERIAL"}]
            duplicate_codes = {issue.code for issue in duplicate_issues}
            duplicate_reason = (
                "PHONE_AND_SERIAL" if len(duplicate_codes) == 2 else
                "PHONE" if "DUPLICATE_PHONE" in duplicate_codes else
                "SERIAL" if "DUPLICATE_SERIAL" in duplicate_codes else None
            )
            reference_id = next((issue.existing_id for issue in duplicate_issues if issue.existing_id is not None), None)
            if reference_id is None:
                reference_id = next((registered_by_row.get(issue.matched_row_number) for issue in duplicate_issues
                                     if issue.source == "file" and issue.matched_row_number in registered_by_row), None)
            application = RecallApplication(
                upload_batch_id=batch.id,
                source_row_number=row_number,
                application_date=data.get("application_date"),
                quantity=data.get("quantity"),
                customer_name=data["customer_name"],
                phone_original=data["phone_original"],
                phone_normalized=data["phone_normalized"] or "",
                address=data["address"],
                memo=data.get("memo"),
                serial_number=data.get("serial_number"),
                lot_number=data.get("lot_number"),
                pickup_agreement=data.get("pickup_agreement"),
                pickup_date=data.get("pickup_date"),
                replacement_shipping_agreement=data.get("replacement_shipping_agreement"),
                current_status=REVIEW_REQUIRED if any(issue.code == "REVIEW_REQUIRED" for issue in row.issues)
                else APPLICATION_RECEIVED,
                duplicate_flag=bool(duplicate_reason),
                duplicate_reason=duplicate_reason,
                duplicate_reference_id=reference_id,
                created_by=user_id,
            )
            db.add(application)
            db.flush()
            db.add(RecallStatusHistory(
                recall_application_id=application.id,
                previous_status=None,
                new_status=application.current_status,
                changed_by=user_id,
                change_type="EXCEL_REGISTRATION",
                reason="접수 데이터 Excel 등록",
            ))
            registered += 1
            registered_by_row[row_number] = application.id
            if duplicate_reason:
                duplicate += 1
            elif row.status == "review":
                review += 1
            else:
                normal += 1
            results.append({"row_number": row_number, "result": "REGISTERED_DUPLICATE" if duplicate_reason else
                            "REGISTERED_REVIEW" if row.status == "review" else "REGISTERED", "application_id": application.id})

        batch.registered_count = int(batch.registered_count or 0) + registered
        batch_id = batch.id
        db.commit()
    except Exception:
        db.rollback()
        raise

    unselected_review = sum(
        1 for row in preview.rows if row.status == "review" and row.raw_row_number not in selected
    )
    return CommitResult(batch_id, registered, duplicate, rejected, unselected_review, tuple(results),
                        normal, review, already_registered)


def list_recall_applications(
    db: Session,
    *,
    keyword: Optional[str],
    status: Optional[str],
    page: int,
    page_size: int,
    duplicate_only: bool = False,
) -> dict:
    conditions = [RecallApplication.duplicate_flag.is_(duplicate_only)]
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


def resolve_recall_duplicate(db: Session, *, application_id: int, action: str, reason: str, user_id: int) -> dict:
    if action not in {"NORMAL", "KEEP"}:
        raise ValueError("중복 처리 방식을 선택해주세요.")
    cleaned_reason = (reason or "").strip()
    if not cleaned_reason or len(cleaned_reason) > 255:
        raise ValueError("처리 사유는 1~255자로 입력해주세요.")
    allowed_reasons = {
        "NORMAL": {"별도 접수 확인", "잘못된 중복 판정"},
        "KEEP": {"실제 중복 확인", "추가 검토 필요"},
    }
    if cleaned_reason not in allowed_reasons[action]:
        raise ValueError("제공된 처리 사유 중 하나를 선택해주세요.")
    try:
        application = db.scalar(select(RecallApplication).where(RecallApplication.id == application_id).with_for_update())
        if application is None:
            raise LookupError("리콜 접수 데이터를 찾을 수 없습니다.")
        if not application.duplicate_flag:
            raise ValueError("중복 확인 대상이 아닙니다.")
        application.duplicate_flag = action != "NORMAL"
        application.duplicate_resolution = action
        application.duplicate_resolved_at = datetime.now(timezone.utc)
        application.duplicate_resolved_by = user_id
        db.add(RecallDuplicateResolutionHistory(
            recall_application_id=application_id, action=action,
            reason=cleaned_reason, changed_by=user_id,
        ))
        db.commit()
        return {"id": application_id, "duplicate_flag": application.duplicate_flag,
                "duplicate_resolution": action}
    except Exception:
        db.rollback()
        raise


def get_recall_summary(db: Session) -> dict:
    status_counts = {
        status: int(count) for status, count in db.execute(
            select(RecallApplication.current_status, func.count())
            .group_by(RecallApplication.current_status)
        ).all()
    }
    registered_count = sum(status_counts.values())
    received_count = status_counts.get(APPLICATION_RECEIVED, 0)
    return {
        "total_count": _get_total_target_count(registered_count),
        "received_count": received_count,
        "remaining_count": status_counts.get(APPLICATION_RECEIVED, 0),
        "in_progress_count": status_counts.get(IN_PROGRESS, 0),
        "shipped_count": status_counts.get(SHIPPED, 0),
    }


def _get_total_target_count(registered_application_count: int) -> int:
    # Until recall Raw Data has its own source, every registered application is a target.
    return registered_application_count


MANUAL_TRANSITIONS = {
    APPLICATION_RECEIVED: (IN_PROGRESS, REVIEW_REQUIRED, STOPPED),
    IN_PROGRESS: (REVIEW_REQUIRED, STOPPED),
    REVIEW_REQUIRED: (APPLICATION_RECEIVED, STOPPED),
    STOPPED: (APPLICATION_RECEIVED, REVIEW_REQUIRED),
    SHIPPED: (APPLICATION_RECEIVED,),
}
BULK_TRANSITIONS = {
    APPLICATION_RECEIVED: IN_PROGRESS,
    IN_PROGRESS: SHIPPED,
}


def bulk_change_recall_applications(
    db: Session, *, ids: Sequence[int], status: str, reason: str, user_id: int
) -> dict:
    if status not in BULK_TRANSITIONS.values():
        raise ValueError("일괄 변경은 진행중 또는 발송 완료만 지원합니다.")
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
        if len(applications) != len(ids):
            db.rollback()
            raise ValueError("선택한 항목 중 찾을 수 없는 접수 데이터가 있습니다.")
        current_statuses = {applications[application_id].current_status for application_id in ids}
        if len(current_statuses) != 1:
            db.rollback()
            raise ValueError("같은 상태의 항목만 선택해야 합니다.")
        previous_status = current_statuses.pop()
        if BULK_TRANSITIONS.get(previous_status) != status:
            db.rollback()
            raise ValueError("선택한 항목은 허용된 다음 단계로만 변경할 수 있습니다.")

        for application_id in ids:
            applications[application_id].current_status = status
            db.add(RecallStatusHistory(
                recall_application_id=application_id,
                previous_status=previous_status,
                new_status=status,
                changed_by=user_id,
                change_type="BULK",
                reason=cleaned_reason,
            ))
        db.commit()
        return {
            "requested": len(ids), "updated": len(ids), "skipped": 0, "failed": 0,
            "results": [{"id": application_id, "result": "UPDATED", "reason_code": None} for application_id in ids],
        }
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
    duplicate_history = list(db.scalars(
        select(RecallDuplicateResolutionHistory)
        .where(RecallDuplicateResolutionHistory.recall_application_id == application_id)
        .order_by(RecallDuplicateResolutionHistory.changed_at.desc(), RecallDuplicateResolutionHistory.id.desc())
    ).all())
    user_ids = {application.created_by}
    user_ids.update(item.changed_by for item in history)
    user_ids.update(item.changed_by for item in duplicate_history)
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
        "duplicate_flag": application.duplicate_flag,
        "duplicate_reason": application.duplicate_reason,
        "duplicate_reference_id": application.duplicate_reference_id,
        "duplicate_resolution": application.duplicate_resolution,
        "duplicate_resolved_at": application.duplicate_resolved_at,
        "duplicate_resolved_by": application.duplicate_resolved_by,
        "duplicate_history": [
            {"action": item.action, "reason": item.reason, "changed_at": item.changed_at,
             "changed_by": item.changed_by, "changed_by_name": names.get(item.changed_by)}
            for item in duplicate_history
        ],
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
    if status not in MANUAL_TRANSITIONS:
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
        if status not in MANUAL_TRANSITIONS.get(previous_status, ()):
            db.rollback()
            raise ValueError("허용되지 않은 상태 전이입니다.")

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
