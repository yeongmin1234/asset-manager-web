from datetime import datetime, timezone
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.work_manual import WorkManual
from app.schemas.work_manual import WorkManualCreate, WorkManualUpdate


class WorkManualNotFoundError(Exception):
    pass


def list_work_manuals(db: Session) -> List[WorkManual]:
    statement = (
        select(WorkManual)
        .where(WorkManual.is_active.is_(True))
        .order_by(
            WorkManual.is_pinned.desc(),
            WorkManual.created_at.desc(),
            WorkManual.id.desc(),
        )
    )
    return list(db.scalars(statement).all())


def get_work_manual(db: Session, manual_id: int, increment_view_count: bool = False) -> WorkManual:
    manual = db.get(WorkManual, manual_id)
    if manual is None or not manual.is_active:
        raise WorkManualNotFoundError()
    if increment_view_count:
        manual.view_count = int(manual.view_count or 0) + 1
        db.add(manual)
        db.commit()
        db.refresh(manual)
    return manual


def create_work_manual(db: Session, payload: WorkManualCreate) -> WorkManual:
    manual = WorkManual(
        category=payload.category,
        title=payload.title,
        content=payload.content,
        author=payload.author,
        is_pinned=payload.is_pinned,
    )
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual


def update_work_manual(
    db: Session,
    manual_id: int,
    payload: WorkManualUpdate,
) -> WorkManual:
    manual = get_work_manual(db, manual_id)
    manual.category = payload.category
    manual.title = payload.title
    manual.content = payload.content
    manual.author = payload.author
    manual.is_pinned = payload.is_pinned
    manual.updated_at = datetime.now(timezone.utc)
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual


def delete_work_manual(db: Session, manual_id: int) -> WorkManual:
    manual = get_work_manual(db, manual_id)
    manual.is_active = False
    manual.updated_at = datetime.now(timezone.utc)
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual
