from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.scm_activity_log import ScmActivityLog
from app.models.user import User


router = APIRouter(prefix="/scm", tags=["scm-activity"])
Module = Literal["store", "customer", "consultation", "as", "sales", "logistics", "order"]
Action = Literal["create", "update", "delete", "status_change", "cancel", "dispatch"]

MODULE_NAMES = {
    "store": "매장", "customer": "고객", "consultation": "상담",
    "as": "A/S", "sales": "판매", "logistics": "물류", "order": "발주",
}
ACTION_NAMES = {
    "create": "등록", "update": "수정", "delete": "삭제",
    "status_change": "상태 변경", "cancel": "취소", "dispatch": "출고 처리",
}
ALLOWED_ACTIONS = {
    "store": {"create", "update", "delete"},
    "customer": {"create", "update"},
    "consultation": {"create", "update", "status_change"},
    "as": {"create", "update", "status_change"},
    "sales": {"create", "update", "cancel", "status_change"},
    "logistics": {"create", "update", "dispatch", "status_change"},
    "order": {"create", "update", "status_change"},
}


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    module: Module
    action: Action


def require_scm_access(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin" and "scm_app" not in (user.menu_permissions or []):
        raise HTTPException(status_code=403, detail="SCM 접근 권한이 없습니다.")
    return user


def serialize(row: ScmActivityLog) -> dict:
    return {
        "id": row.id, "user_id": row.user_id, "user_name": row.user_name,
        "module": row.module, "action": row.action, "target_id": row.target_id,
        "message": row.message, "created_at": row.created_at.isoformat(),
    }


@router.post("/activity", status_code=201)
def record_activity(
    payload: ActivityCreate,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_scm_access),
):
    if payload.action not in ALLOWED_ACTIONS[payload.module]:
        raise HTTPException(status_code=422, detail="지원하지 않는 작업 유형입니다.")
    row = ScmActivityLog(
        user_id=user.id,
        user_name=user.name,
        module=payload.module,
        action=payload.action,
        message=f"{MODULE_NAMES[payload.module]} {ACTION_NAMES[payload.action]} (미리보기)",
        ip_address=request.client.host if request.client else None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@router.get("/dashboard")
def scm_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_scm_access),
):
    rows = db.scalars(select(ScmActivityLog).order_by(ScmActivityLog.created_at.desc(), ScmActivityLog.id.desc()).limit(20)).all()
    return {"recent_activity": [serialize(row) for row in rows]}


@router.get("/activity")
def list_activity(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user: Optional[str] = Query(default=None, max_length=100),
    module: Optional[Module] = None,
    action: Optional[Action] = None,
    keyword: Optional[str] = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_scm_access),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="날짜 범위를 확인해 주세요.")
    statement = select(ScmActivityLog)
    if start_date:
        statement = statement.where(ScmActivityLog.created_at >= datetime.combine(start_date, time.min, timezone.utc))
    if end_date:
        statement = statement.where(ScmActivityLog.created_at < datetime.combine(end_date + timedelta(days=1), time.min, timezone.utc))
    if user:
        statement = statement.where(ScmActivityLog.user_name.ilike(f"%{user}%"))
    if module:
        statement = statement.where(ScmActivityLog.module == module)
    if action:
        statement = statement.where(ScmActivityLog.action == action)
    if keyword:
        statement = statement.where(or_(ScmActivityLog.message.ilike(f"%{keyword}%"), ScmActivityLog.user_name.ilike(f"%{keyword}%")))
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(statement.order_by(ScmActivityLog.created_at.desc(), ScmActivityLog.id.desc()).offset(offset).limit(limit)).all()
    return {"items": [serialize(row) for row in rows], "total": total, "limit": limit, "offset": offset}
