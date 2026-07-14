from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.expiration_schedule import (
    ExpirationSchedule,
    ExpirationScheduleCategory,
    ExpirationScheduleStatus,
)
from app.models.user import User
from app.schemas.expiration_schedule import (
    ExpirationScheduleCompleteRequest,
    ExpirationScheduleCreate,
    ExpirationScheduleRead,
    ExpirationScheduleSummary,
    ExpirationScheduleUpdate,
)
from app.services.expiration_schedule_service import (
    ExpirationScheduleNotFoundError,
    complete_expiration_schedule,
    create_expiration_schedule,
    delete_expiration_schedule,
    get_expiration_schedule,
    get_expiration_schedule_summary,
    get_expiration_schedules,
    update_expiration_schedule,
)
from app.services.attachment_service import AttachmentValidationError
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log


router = APIRouter(prefix="/expiration-schedules", tags=["expiration-schedules"])


@router.get("", response_model=List[ExpirationScheduleRead])
def list_expiration_schedules(
    category: Optional[ExpirationScheduleCategory] = Query(default=None),
    schedule_status: Optional[ExpirationScheduleStatus] = Query(default=None, alias="status"),
    keyword: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    is_completed: Optional[bool] = None,
    db: Session = Depends(get_db),
) -> List[ExpirationScheduleRead]:
    try:
        return get_expiration_schedules(
            db,
            category=category,
            status=schedule_status,
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            is_completed=is_completed,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading expiration schedules.",
        ) from exc


@router.get("/summary", response_model=ExpirationScheduleSummary)
def read_expiration_schedule_summary(
    db: Session = Depends(get_db),
) -> ExpirationScheduleSummary:
    try:
        return get_expiration_schedule_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading expiration schedule summary.",
        ) from exc


@router.get("/{schedule_id}", response_model=ExpirationScheduleRead)
def read_expiration_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
) -> ExpirationScheduleRead:
    try:
        return get_expiration_schedule(db, schedule_id)
    except ExpirationScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expiration schedule not found.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading expiration schedule.",
        ) from exc


@router.post("", response_model=ExpirationScheduleRead, status_code=status.HTTP_201_CREATED)
def create_new_expiration_schedule(
    request: Request,
    payload: ExpirationScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpirationScheduleRead:
    try:
        result = create_expiration_schedule(
            db,
            payload,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="expiration_schedules", menu_name="점검·만료 관리", target_type="expiration_schedule", target_id=result.id, target_name=result.title, action_summary="점검·만료 일정을 등록했습니다.", after_data=audit_snapshot(result, ("category", "title", "target_name", "due_date", "status", "is_completed", "memo")))
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating expiration schedule.",
        ) from exc


@router.put("/{schedule_id}", response_model=ExpirationScheduleRead)
def update_existing_expiration_schedule(
    request: Request,
    schedule_id: int,
    payload: ExpirationScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpirationScheduleRead:
    try:
        fields = ("category", "title", "target_name", "due_date", "status", "is_completed", "memo")
        before = audit_snapshot(db.get(ExpirationSchedule, schedule_id), fields)
        result = update_expiration_schedule(
            db,
            schedule_id,
            payload,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="expiration_schedules", menu_name="점검·만료 관리", target_type="expiration_schedule", target_id=result.id, target_name=result.title, action_summary="점검·만료 일정을 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except ExpirationScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expiration schedule not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating expiration schedule.",
        ) from exc


@router.patch("/{schedule_id}/complete", response_model=ExpirationScheduleRead)
def complete_existing_expiration_schedule(
    request: Request,
    schedule_id: int,
    payload: ExpirationScheduleCompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpirationScheduleRead:
    try:
        fields = ("status", "is_completed", "completed_at")
        before = audit_snapshot(db.get(ExpirationSchedule, schedule_id), fields)
        result = complete_expiration_schedule(
            db,
            schedule_id,
            payload,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, fields))
        record_audit_log(db, request, current_user, action_type="update", menu_key="expiration_schedules", menu_name="점검·만료 관리", target_type="expiration_schedule", target_id=result.id, target_name=result.title, action_summary="점검·만료 일정을 완료 처리했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
    except ExpirationScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expiration schedule not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while completing expiration schedule.",
        ) from exc


@router.delete("/{schedule_id}", response_model=ExpirationScheduleRead)
def delete_existing_expiration_schedule(
    request: Request,
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ExpirationScheduleRead:
    try:
        before = audit_snapshot(db.get(ExpirationSchedule, schedule_id), ("category", "title", "target_name", "due_date", "status", "is_completed"))
        result = delete_expiration_schedule(
            db,
            schedule_id,
            current_user=current_user,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="delete", menu_key="expiration_schedules", menu_name="점검·만료 관리", target_type="expiration_schedule", target_id=result.id, target_name=result.title, action_summary="점검·만료 일정을 삭제했습니다.", before_data=before)
        return result
    except ExpirationScheduleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expiration schedule not found.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting expiration schedule.",
        ) from exc
