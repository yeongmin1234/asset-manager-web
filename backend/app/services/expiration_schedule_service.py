from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.expiration_schedule import (
    ExpirationSchedule,
    ExpirationScheduleCategory,
    ExpirationScheduleStatus,
)
from app.models.attachment import AttachmentEntityType
from app.models.user import User
from app.schemas.expiration_schedule import (
    ExpirationScheduleCompleteRequest,
    ExpirationScheduleCreate,
    ExpirationScheduleRead,
    ExpirationScheduleSummary,
    ExpirationScheduleUpdate,
)
from app.services.activity_log_service import record_activity_log
from app.services.attachment_service import ensure_no_attachments


class ExpirationScheduleNotFoundError(Exception):
    pass


STATUS_PRIORITY = {
    ExpirationScheduleStatus.OVERDUE: 0,
    ExpirationScheduleStatus.WITHIN_7_DAYS: 1,
    ExpirationScheduleStatus.WITHIN_30_DAYS: 2,
    ExpirationScheduleStatus.NORMAL: 3,
    ExpirationScheduleStatus.COMPLETED: 4,
}


def calculate_days_left(due_date: date, today: Optional[date] = None) -> int:
    base_date = today or date.today()
    return (due_date - base_date).days


def calculate_schedule_status(
    due_date: date,
    is_completed: bool,
    today: Optional[date] = None,
) -> ExpirationScheduleStatus:
    if is_completed:
        return ExpirationScheduleStatus.COMPLETED
    days_left = calculate_days_left(due_date, today)
    if days_left < 0:
        return ExpirationScheduleStatus.OVERDUE
    if days_left <= 7:
        return ExpirationScheduleStatus.WITHIN_7_DAYS
    if days_left <= 30:
        return ExpirationScheduleStatus.WITHIN_30_DAYS
    return ExpirationScheduleStatus.NORMAL


def get_expiration_schedules(
    db: Session,
    *,
    category: Optional[ExpirationScheduleCategory] = None,
    status: Optional[ExpirationScheduleStatus] = None,
    keyword: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_completed: Optional[bool] = None,
) -> List[ExpirationSchedule]:
    statement = select(ExpirationSchedule)
    if category is not None:
        statement = statement.where(ExpirationSchedule.category == category)
    if date_from is not None:
        statement = statement.where(ExpirationSchedule.due_date >= date_from)
    if date_to is not None:
        statement = statement.where(ExpirationSchedule.due_date <= date_to)
    if is_completed is not None:
        statement = statement.where(ExpirationSchedule.is_completed.is_(is_completed))
    if keyword:
        keyword_pattern = "%{}%".format(keyword.strip())
        if keyword_pattern != "%%":
            statement = statement.where(
                or_(
                    ExpirationSchedule.title.ilike(keyword_pattern),
                    ExpirationSchedule.target_name.ilike(keyword_pattern),
                    ExpirationSchedule.memo.ilike(keyword_pattern),
                )
            )

    items = list(db.scalars(statement).all())
    prepared_items = [_prepare_schedule(item) for item in items]
    if status is not None:
        prepared_items = [item for item in prepared_items if item.status == status]
    return sorted(
        prepared_items,
        key=lambda item: (
            STATUS_PRIORITY.get(item.status, 9),
            item.due_date,
            item.id,
        ),
    )


def get_expiration_schedule(db: Session, schedule_id: int) -> ExpirationSchedule:
    schedule = db.get(ExpirationSchedule, schedule_id)
    if schedule is None:
        raise ExpirationScheduleNotFoundError(
            "Expiration schedule not found: {}".format(schedule_id)
        )
    return _prepare_schedule(schedule)


def create_expiration_schedule(
    db: Session,
    payload: ExpirationScheduleCreate,
    *,
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ExpirationSchedule:
    now = datetime.now(timezone.utc)
    schedule = ExpirationSchedule(**payload.model_dump())
    schedule.status = calculate_schedule_status(schedule.due_date, False)
    schedule.is_completed = False
    schedule.completed_at = None
    schedule.created_by = _get_user_label(current_user)
    schedule.updated_by = _get_user_label(current_user)
    schedule.updated_at = now
    db.add(schedule)
    db.flush()
    _record_schedule_activity(
        db,
        schedule,
        action_type="create",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="일정 등록: {}".format(schedule.title),
        after_data=_serialize_schedule(schedule),
    )
    db.commit()
    db.refresh(schedule)
    return _prepare_schedule(schedule)


def update_expiration_schedule(
    db: Session,
    schedule_id: int,
    payload: ExpirationScheduleUpdate,
    *,
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ExpirationSchedule:
    schedule = get_expiration_schedule(db, schedule_id)
    ensure_no_attachments(db, AttachmentEntityType.EXPIRATION_SCHEDULE, schedule_id)
    before_data = _serialize_schedule(schedule)
    payload_data = payload.model_dump()
    is_completed = bool(payload_data.pop("is_completed"))
    for field_name, value in payload_data.items():
        setattr(schedule, field_name, value)
    _apply_completion(schedule, is_completed)
    schedule.status = calculate_schedule_status(schedule.due_date, schedule.is_completed)
    schedule.updated_by = _get_user_label(current_user)
    schedule.updated_at = datetime.now(timezone.utc)
    db.flush()
    _record_schedule_activity(
        db,
        schedule,
        action_type="update",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="일정 수정: {}".format(schedule.title),
        before_data=before_data,
        after_data=_serialize_schedule(schedule),
    )
    db.commit()
    db.refresh(schedule)
    return _prepare_schedule(schedule)


def complete_expiration_schedule(
    db: Session,
    schedule_id: int,
    payload: ExpirationScheduleCompleteRequest,
    *,
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ExpirationSchedule:
    schedule = get_expiration_schedule(db, schedule_id)
    before_data = _serialize_schedule(schedule)
    _apply_completion(schedule, payload.is_completed)
    schedule.status = calculate_schedule_status(schedule.due_date, schedule.is_completed)
    schedule.updated_by = _get_user_label(current_user)
    schedule.updated_at = datetime.now(timezone.utc)
    db.flush()
    action_label = "일정 완료" if schedule.is_completed else "일정 완료 취소"
    _record_schedule_activity(
        db,
        schedule,
        action_type="complete" if schedule.is_completed else "reopen",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="{}: {}".format(action_label, schedule.title),
        before_data=before_data,
        after_data=_serialize_schedule(schedule),
    )
    db.commit()
    db.refresh(schedule)
    return _prepare_schedule(schedule)


def delete_expiration_schedule(
    db: Session,
    schedule_id: int,
    *,
    current_user: User,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ExpirationScheduleRead:
    schedule = get_expiration_schedule(db, schedule_id)
    before_data = _serialize_schedule(schedule)
    deleted_schedule = _to_read(schedule)
    _record_schedule_activity(
        db,
        schedule,
        action_type="delete",
        current_user=current_user,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary="일정 삭제: {}".format(schedule.title),
        before_data=before_data,
    )
    db.delete(schedule)
    db.commit()
    return deleted_schedule


def get_expiration_schedule_summary(db: Session) -> ExpirationScheduleSummary:
    schedules = [_prepare_schedule(item) for item in db.scalars(select(ExpirationSchedule)).all()]
    summary = ExpirationScheduleSummary()
    for schedule in schedules:
        if schedule.status == ExpirationScheduleStatus.OVERDUE:
            summary.overdue_count += 1
        elif schedule.status == ExpirationScheduleStatus.WITHIN_7_DAYS:
            summary.within_7_days_count += 1
        elif schedule.status == ExpirationScheduleStatus.WITHIN_30_DAYS:
            summary.within_30_days_count += 1
        elif schedule.status == ExpirationScheduleStatus.COMPLETED:
            summary.completed_count += 1
        else:
            summary.normal_count += 1

    upcoming = [
        schedule
        for schedule in schedules
        if schedule.status
        in {
            ExpirationScheduleStatus.OVERDUE,
            ExpirationScheduleStatus.WITHIN_7_DAYS,
            ExpirationScheduleStatus.WITHIN_30_DAYS,
        }
    ]
    summary.upcoming_items = [
        _to_read(schedule)
        for schedule in sorted(
            upcoming,
            key=lambda item: (
                STATUS_PRIORITY.get(item.status, 9),
                item.due_date,
                item.id,
            ),
        )[:5]
    ]
    return summary


def _prepare_schedule(schedule: ExpirationSchedule) -> ExpirationSchedule:
    schedule.status = calculate_schedule_status(schedule.due_date, schedule.is_completed)
    schedule.days_left = calculate_days_left(schedule.due_date)
    return schedule


def _to_read(schedule: ExpirationSchedule) -> ExpirationScheduleRead:
    prepared = _prepare_schedule(schedule)
    return ExpirationScheduleRead.model_validate(prepared)


def _apply_completion(schedule: ExpirationSchedule, is_completed: bool) -> None:
    next_completed = bool(is_completed)
    if next_completed and not schedule.is_completed:
        schedule.completed_at = datetime.now(timezone.utc)
    if not next_completed:
        schedule.completed_at = None
    schedule.is_completed = next_completed


def _record_schedule_activity(
    db: Session,
    schedule: ExpirationSchedule,
    *,
    action_type: str,
    current_user: User,
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: str,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> None:
    record_activity_log(
        db,
        menu_name="점검·만료 관리",
        action_type=action_type,
        target_type="expiration_schedule",
        target_id=schedule.id,
        target_name=schedule.title,
        actor_ip=actor_ip,
        actor_name=_get_user_label(current_user),
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def _serialize_schedule(schedule: ExpirationSchedule) -> Dict[str, object]:
    prepared = _prepare_schedule(schedule)
    return {
        "category": _enum_value(prepared.category),
        "title": prepared.title,
        "target_name": prepared.target_name,
        "due_date": prepared.due_date.isoformat(),
        "notification_days": prepared.notification_days,
        "status": _enum_value(prepared.status),
        "memo": prepared.memo,
        "source_type": prepared.source_type,
        "source_id": prepared.source_id,
        "is_completed": prepared.is_completed,
        "completed_at": prepared.completed_at.isoformat() if prepared.completed_at else None,
        "created_by": prepared.created_by,
        "updated_by": prepared.updated_by,
        "days_left": prepared.days_left,
    }


def _enum_value(value: object) -> object:
    return value.value if hasattr(value, "value") else value


def _get_user_label(user: User) -> str:
    return user.name or user.username
