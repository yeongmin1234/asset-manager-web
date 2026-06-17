from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.software_item import SoftwareItem, SoftwareLicenseType
from app.schemas.software import (
    SoftwareItemCreate,
    SoftwareItemRead,
    SoftwareItemUpdate,
    SoftwareStatsSummary,
)
from app.services.activity_log_service import (
    record_software_activity,
    serialize_software_activity_data,
)


class SoftwareItemNotFoundError(Exception):
    pass


def get_software_items(
    db: Session,
    *,
    keyword: Optional[str] = None,
    license_type: Optional[SoftwareLicenseType] = None,
) -> List[SoftwareItem]:
    statement = select(SoftwareItem)

    if keyword:
        keyword_pattern = f"%{keyword.strip()}%"
        if keyword_pattern != "%%":
            statement = statement.where(
                or_(
                    SoftwareItem.name.ilike(keyword_pattern),
                    SoftwareItem.owner_name.ilike(keyword_pattern),
                    SoftwareItem.note.ilike(keyword_pattern),
                )
            )

    if license_type is not None:
        statement = statement.where(SoftwareItem.license_type == license_type)

    statement = statement.order_by(SoftwareItem.created_at.desc(), SoftwareItem.id.desc())
    return list(db.scalars(statement).all())


def create_software_item(
    db: Session,
    payload: SoftwareItemCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SoftwareItem:
    software_item = SoftwareItem(**payload.model_dump())
    db.add(software_item)
    db.flush()
    record_software_activity(
        db,
        action_type="create",
        target_id=software_item.id,
        target_name=software_item.name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"SW 등록: {software_item.name}",
        after_data=serialize_software_activity_data(software_item),
    )
    db.commit()
    db.refresh(software_item)
    return software_item


def get_software_item(db: Session, software_id: int) -> SoftwareItem:
    software_item = db.scalar(
        select(SoftwareItem).where(SoftwareItem.id == software_id)
    )
    if software_item is None:
        raise SoftwareItemNotFoundError(f"Software item not found: {software_id}")
    return software_item


def update_software_item(
    db: Session,
    software_id: int,
    payload: SoftwareItemUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SoftwareItem:
    software_item = get_software_item(db, software_id)
    before_data = serialize_software_activity_data(software_item)
    for field_name, value in payload.model_dump().items():
        setattr(software_item, field_name, value)
    software_item.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_software_activity(
        db,
        action_type="update",
        target_id=software_item.id,
        target_name=software_item.name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"SW 수정: {software_item.name}",
        before_data=before_data,
        after_data=serialize_software_activity_data(software_item),
    )
    db.commit()
    db.refresh(software_item)
    return software_item


def delete_software_item(
    db: Session,
    software_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SoftwareItemRead:
    software_item = get_software_item(db, software_id)
    before_data = serialize_software_activity_data(software_item)
    deleted_item = SoftwareItemRead.model_validate(software_item)
    record_software_activity(
        db,
        action_type="delete",
        target_id=software_item.id,
        target_name=software_item.name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"SW 삭제: {software_item.name}",
        before_data=before_data,
    )
    db.delete(software_item)
    db.commit()
    return deleted_item


def get_software_stats_summary(db: Session) -> SoftwareStatsSummary:
    row = db.execute(
        select(
            func.count(SoftwareItem.id).label("total_software"),
            func.coalesce(
                func.sum(
                    case(
                        (SoftwareItem.license_type == SoftwareLicenseType.PERPETUAL, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("perpetual_count"),
            func.coalesce(
                func.sum(
                    case(
                        (SoftwareItem.license_type == SoftwareLicenseType.SUBSCRIPTION, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("subscription_count"),
            func.coalesce(
                func.sum(
                    case(
                        (SoftwareItem.license_type == SoftwareLicenseType.DISCONTINUED, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("discontinued_count"),
        )
    ).one()

    return SoftwareStatsSummary(
        total_software=int(row.total_software or 0),
        perpetual_count=int(row.perpetual_count or 0),
        subscription_count=int(row.subscription_count or 0),
        discontinued_count=int(row.discontinued_count or 0),
    )
