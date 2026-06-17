from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.activity_log import ActivityLogRead
from app.services.activity_log_service import get_activity_logs


router = APIRouter(prefix="/activity-logs", tags=["activity-logs"])


@router.get("", response_model=List[ActivityLogRead])
def list_activity_logs(
    limit: int = Query(default=100, ge=1, le=200),
    target_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> List[ActivityLogRead]:
    try:
        return get_activity_logs(db, limit=limit, target_type=target_type)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading activity logs.",
        ) from exc


@router.get("/recent", response_model=List[ActivityLogRead])
def list_recent_activity_logs(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> List[ActivityLogRead]:
    try:
        return get_activity_logs(db, limit=limit)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading activity logs.",
        ) from exc
