"""Conservative matching of raw recall targets to actual applications."""

from datetime import datetime, timezone
from typing import Dict, Optional, Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models.recall_application import IN_PROGRESS, ORDER_CONFIRMED, ORDER_EXPORTED, SHIPPED, RecallApplication
from app.models.recall_target import RecallTarget
from app.services.recall_application_excel import _serial_key, _valid_phone


UNMATCHED = "UNMATCHED"
MATCHED = "MATCHED"
REVIEW = "REVIEW"


def _phone_key(value):
    return value if value and len(value) in (10, 11) and _valid_phone(value) else None


def _clear(target: RecallTarget, status: str, reason: Optional[str] = None):
    target.match_status = status
    target.matched_application_id = None
    target.matched_at = None
    target.matched_by = None
    target.match_method = None
    target.match_review_reason = reason


def run_auto_matching(db: Session, *, user_id: int, target_ids: Optional[Sequence[int]] = None) -> Dict[str, int]:
    """Match only pending targets in the caller's transaction; never rewrite MATCHED."""
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(714257001)"))
    applications = db.scalars(select(RecallApplication).where(RecallApplication.is_deleted.is_(False)).order_by(RecallApplication.id)).all()
    serials, phones = {}, {}
    for application in applications:
        serial = _serial_key(application.serial_number)
        phone = _phone_key(application.phone_normalized)
        if serial:
            serials.setdefault(serial, []).append(application)
        if phone:
            phones.setdefault(phone, []).append(application)
    occupied = {application_id: target_id for application_id, target_id in db.execute(
        select(RecallTarget.matched_application_id, RecallTarget.id).where(RecallTarget.matched_application_id.is_not(None))
    ).all()}
    query = select(RecallTarget).where(RecallTarget.is_deleted.is_(False), RecallTarget.match_status.in_((UNMATCHED, REVIEW)))
    if target_ids is not None:
        query = query.where(RecallTarget.id.in_(target_ids))
    targets = db.scalars(query.order_by(RecallTarget.id).with_for_update()).all()
    counts = {"matched": 0, "review": 0, "unmatched": 0}
    for target in targets:
        if target.duplicate_flag:
            _clear(target, REVIEW, "RAW_TARGET_DUPLICATE")
            counts["review"] += 1
            continue
        serial_candidates = serials.get(_serial_key(target.serial_number), []) if target.serial_number else []
        phone_candidates = phones.get(_phone_key(target.phone_normalized), []) if target.phone_normalized else []
        candidate = None
        method = None
        reason = None
        if len(serial_candidates) > 1:
            reason = "MULTIPLE_SERIAL_MATCH"
        elif len(serial_candidates) == 1:
            candidate = serial_candidates[0]
            method = "SERIAL"
            if len(phone_candidates) == 1 and phone_candidates[0].id != candidate.id:
                reason = "SERIAL_PHONE_CONFLICT"
        elif len(phone_candidates) > 1:
            reason = "MULTIPLE_PHONE_MATCH"
        elif len(phone_candidates) == 1:
            candidate = phone_candidates[0]
            method = "PHONE"
        if reason:
            _clear(target, REVIEW, reason)
            counts["review"] += 1
        elif candidate is None:
            _clear(target, UNMATCHED)
            counts["unmatched"] += 1
        elif candidate.duplicate_flag:
            _clear(target, REVIEW, "DUPLICATE_APPLICATION")
            counts["review"] += 1
        elif candidate.id in occupied:
            _clear(target, REVIEW, "APPLICATION_ALREADY_MATCHED")
            counts["review"] += 1
        else:
            target.match_status = MATCHED
            target.matched_application_id = candidate.id
            target.matched_at = datetime.now(timezone.utc)
            target.matched_by = user_id
            target.match_method = method
            target.match_review_reason = None
            occupied[candidate.id] = target.id
            counts["matched"] += 1
    db.flush()
    return counts


def manual_match(db: Session, *, target_id: int, application_id: int, user_id: int):
    try:
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_xact_lock(714257001)"))
        target = db.scalar(select(RecallTarget).where(RecallTarget.id == target_id, RecallTarget.is_deleted.is_(False)).with_for_update())
        application = db.scalar(select(RecallApplication).where(RecallApplication.id == application_id,
                                                                 RecallApplication.is_deleted.is_(False)))
        if target is None or application is None:
            raise LookupError("리콜 대상 또는 신청 건을 찾을 수 없습니다.")
        if target.match_status == MATCHED:
            raise ValueError("기존 매칭을 먼저 해제해주세요.")
        owner = db.scalar(select(RecallTarget.id).where(RecallTarget.matched_application_id == application_id))
        if owner is not None:
            raise ValueError("이미 다른 리콜 대상에 연결된 신청 건입니다.")
        target.match_status = MATCHED
        target.matched_application_id = application_id
        target.matched_at = datetime.now(timezone.utc)
        target.matched_by = user_id
        target.match_method = "MANUAL"
        target.match_review_reason = None
        db.commit()
        return {"target_id": target_id, "application_id": application_id, "match_status": MATCHED, "match_method": "MANUAL"}
    except Exception:
        db.rollback()
        raise


def unmatch(db: Session, *, target_id: int):
    try:
        target = db.scalar(select(RecallTarget).where(RecallTarget.id == target_id, RecallTarget.is_deleted.is_(False)).with_for_update())
        if target is None:
            raise LookupError("리콜 대상을 찾을 수 없습니다.")
        if target.match_status != MATCHED:
            raise ValueError("연결된 신청 건이 없습니다.")
        application_id = target.matched_application_id
        _clear(target, UNMATCHED)
        db.commit()
        return {"target_id": target_id, "application_id": application_id, "match_status": UNMATCHED}
    except Exception:
        db.rollback()
        raise


def matching_summary(db: Session):
    targets = db.scalars(select(RecallTarget).where(RecallTarget.is_deleted.is_(False))).all()
    matched = [target for target in targets if target.match_status == MATCHED]
    ids = [target.matched_application_id for target in matched]
    applications = {item.id: item for item in db.scalars(select(RecallApplication).where(
        RecallApplication.id.in_(ids), RecallApplication.is_deleted.is_(False))).all()} if ids else {}
    current_matches = [target for target in matched if target.matched_application_id in applications]
    return {"total_count": len(targets), "received_count": len(current_matches),
            "remaining_count": len(targets) - len(current_matches),
            "in_progress_count": sum(applications[target.matched_application_id].current_status == IN_PROGRESS
                                     for target in current_matches),
            "order_count": sum(applications[target.matched_application_id].order_status in (ORDER_EXPORTED, ORDER_CONFIRMED)
                               for target in current_matches),
            "shipped_count": sum(applications[target.matched_application_id].current_status == SHIPPED
                                 for target in current_matches)}


def channel_summary(db: Session):
    targets = db.scalars(select(RecallTarget).where(RecallTarget.is_deleted.is_(False))).all()
    ids = [target.matched_application_id for target in targets if target.match_status == MATCHED]
    applications = {item.id: item for item in db.scalars(select(RecallApplication).where(
        RecallApplication.id.in_(ids), RecallApplication.is_deleted.is_(False))).all()} if ids else {}
    channels = {}
    for target in targets:
        name = target.sales_channel or "미지정"
        item = channels.setdefault(name, {"sales_channel": name, "total_count": 0, "matched_count": 0,
                                          "unmatched_count": 0, "review_count": 0, "in_progress_count": 0,
                                          "shipped_count": 0, "application_rate": 0.0})
        item["total_count"] += 1
        if target.match_status == MATCHED and target.matched_application_id in applications:
            item["matched_count"] += 1
            application = applications.get(target.matched_application_id)
            if application and application.current_status == IN_PROGRESS:
                item["in_progress_count"] += 1
            if application and application.current_status == SHIPPED:
                item["shipped_count"] += 1
        elif target.match_status == REVIEW:
            item["review_count"] += 1
        else:
            item["unmatched_count"] += 1
    for item in channels.values():
        item["application_rate"] = round(100.0 * item["matched_count"] / item["total_count"], 2)
    return [channels[name] for name in sorted(channels)]
