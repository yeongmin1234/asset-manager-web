from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.dashboard_notice import DashboardNotice
from app.schemas.dashboard_notice import DashboardNoticeCreate, DashboardNoticeUpdate


class DashboardNoticeNotFoundError(Exception):
    pass


def list_dashboard_notices(db: Session) -> List[DashboardNotice]:
    statement = (
        select(DashboardNotice)
        .where(DashboardNotice.is_active.is_(True))
        .order_by(
            DashboardNotice.is_pinned.desc(),
            DashboardNotice.created_at.desc(),
            DashboardNotice.id.desc(),
        )
    )
    return list(db.scalars(statement).all())


def get_dashboard_notice(db: Session, notice_id: int) -> DashboardNotice:
    notice = db.get(DashboardNotice, notice_id)
    if notice is None or not notice.is_active:
        raise DashboardNoticeNotFoundError()
    return notice


def create_dashboard_notice(db: Session, payload: DashboardNoticeCreate) -> DashboardNotice:
    notice = DashboardNotice(
        notice_type=payload.notice_type.value,
        title=payload.title,
        content=payload.content,
        is_pinned=payload.is_pinned,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


def update_dashboard_notice(
    db: Session,
    notice_id: int,
    payload: DashboardNoticeUpdate,
) -> DashboardNotice:
    notice = get_dashboard_notice(db, notice_id)
    notice.notice_type = payload.notice_type.value
    notice.title = payload.title
    notice.content = payload.content
    notice.is_pinned = payload.is_pinned
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


def delete_dashboard_notice(db: Session, notice_id: int) -> DashboardNotice:
    notice = get_dashboard_notice(db, notice_id)
    notice.is_active = False
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice
