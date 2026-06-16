from datetime import date, datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_log import SystemActivityLog
from app.models.software_item import SoftwareItem


SOFTWARE_LOG_FIELDS = (
    "name",
    "owner_name",
    "license_type",
    "quantity",
    "expire_date",
)


def serialize_software_activity_data(item: SoftwareItem) -> Dict[str, object]:
    data: Dict[str, object] = {}
    for field_name in SOFTWARE_LOG_FIELDS:
        value = getattr(item, field_name)
        if isinstance(value, (date, datetime)):
            data[field_name] = value.isoformat()
        elif hasattr(value, "value"):
            data[field_name] = value.value
        else:
            data[field_name] = value
    return data


def record_software_activity(
    db: Session,
    *,
    action_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    log = SystemActivityLog(
        menu_name="SW 현황",
        action_type=action_type,
        target_type="software",
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        actor_name=None,
        user_agent=user_agent,
        before_data=before_data,
        after_data=after_data,
    )
    db.add(log)
    return log


def get_activity_logs(db: Session, limit: int = 100) -> List[SystemActivityLog]:
    safe_limit = min(max(limit, 1), 200)
    statement = (
        select(SystemActivityLog)
        .order_by(SystemActivityLog.created_at.desc(), SystemActivityLog.id.desc())
        .limit(safe_limit)
    )
    return list(db.scalars(statement).all())
