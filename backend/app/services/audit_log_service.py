import logging
import math
from decimal import Decimal
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional

from fastapi import Request
from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogPage
from app.services.login_access_log_service import classify_access_type, get_client_ip, parse_user_agent


logger = logging.getLogger(__name__)
ALLOWED_ACTION_TYPES = {
    "create", "update", "delete", "activate", "deactivate",
    "permission_change", "excel_import", "export",
}
SENSITIVE_FIELD_PARTS = (
    "password", "token", "jwt", "cookie", "session", "secret", "api_key",
    "apikey", "webhook", "database_url", "private_key", "license_key",
    "credential", "nas_password", "scm_password", "비밀번호", "인증정보",
)


def record_audit_log(
    db: Session,
    request: Request,
    current_user: User,
    *,
    action_type: str,
    menu_key: str,
    menu_name: str,
    target_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    action_summary: str,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    changed_fields: Optional[list] = None,
) -> bool:
    if action_type not in ALLOWED_ACTION_TYPES:
        logger.error("Rejected unsupported audit action type: %s", action_type)
        return False
    audit_db = Session(bind=db.get_bind())
    try:
        ip_address = get_client_ip(request)
        user_agent = (request.headers.get("user-agent") or "").strip() or None
        browser, operating_system = parse_user_agent(user_agent)
        safe_before = sanitize_audit_data(before_data)
        safe_after = sanitize_audit_data(after_data)
        calculated_fields = changed_fields
        if calculated_fields is None and (safe_before is not None or safe_after is not None):
            safe_before, safe_after, calculated_fields = build_audit_changes(safe_before, safe_after)
        audit_db.add(AuditLog(
            user_id=current_user.id,
            username=current_user.username,
            user_name=current_user.name,
            action_type=action_type,
            menu_key=menu_key[:50],
            menu_name=menu_name[:100],
            target_type=target_type[:50],
            target_id=target_id,
            target_name=(target_name or "")[:200] or None,
            action_summary=action_summary[:500],
            before_data=safe_before,
            after_data=safe_after,
            changed_fields=calculated_fields or None,
            ip_address=ip_address,
            access_type=classify_access_type(ip_address),
            user_agent=user_agent,
            browser=browser,
            operating_system=operating_system,
        ))
        audit_db.commit()
        return True
    except Exception:
        audit_db.rollback()
        logger.exception("Failed to record audit log")
        return False
    finally:
        audit_db.close()


def get_audit_logs(
    db: Session, *, keyword: Optional[str], username: Optional[str],
    action_type: Optional[str], menu_key: Optional[str], target_type: Optional[str],
    access_type: Optional[str], start_date: Optional[date], end_date: Optional[date],
    page: int, page_size: int, changed_field: Optional[str] = None,
) -> AuditLogPage:
    conditions = []
    if keyword and keyword.strip():
        pattern = "%{}%".format(keyword.strip())
        conditions.append(or_(
            AuditLog.username.ilike(pattern), AuditLog.user_name.ilike(pattern),
            AuditLog.target_name.ilike(pattern), AuditLog.action_summary.ilike(pattern),
            AuditLog.ip_address.ilike(pattern),
        ))
    if username and username.strip():
        pattern = "%{}%".format(username.strip())
        conditions.append(or_(AuditLog.username.ilike(pattern), AuditLog.user_name.ilike(pattern)))
    if action_type:
        conditions.append(AuditLog.action_type == action_type)
    if menu_key:
        conditions.append(AuditLog.menu_key == menu_key)
    if target_type:
        conditions.append(AuditLog.target_type == target_type)
    if access_type:
        conditions.append(AuditLog.access_type == access_type)
    if changed_field and changed_field.strip():
        conditions.append(cast(AuditLog.changed_fields, String).ilike("%{}%".format(changed_field.strip())))
    if start_date:
        conditions.append(AuditLog.occurred_at >= datetime.combine(start_date, time.min))
    if end_date:
        conditions.append(AuditLog.occurred_at < datetime.combine(end_date + timedelta(days=1), time.min))

    filtered = select(AuditLog).where(*conditions)
    total = int(db.scalar(select(func.count()).select_from(filtered.subquery())) or 0)
    items = list(db.scalars(
        filtered.order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all())
    menu_options = [
        {"menu_key": row[0], "menu_name": row[1]}
        for row in db.execute(select(AuditLog.menu_key, AuditLog.menu_name).distinct().order_by(AuditLog.menu_name)).all()
    ]
    target_options = list(db.scalars(select(AuditLog.target_type).distinct().order_by(AuditLog.target_type)).all())
    return AuditLogPage(
        items=items, total=total, page=page, page_size=page_size,
        total_pages=max(1, int(math.ceil(total / float(page_size)))),
        menu_options=menu_options, target_type_options=target_options,
    )


def get_audit_log(db: Session, audit_log_id: int) -> Optional[AuditLog]:
    return db.get(AuditLog, audit_log_id)


def query_audit_logs_for_export(
    db: Session, *, keyword: Optional[str], username: Optional[str], action_type: Optional[str],
    menu_key: Optional[str], target_type: Optional[str], access_type: Optional[str],
    start_date: Optional[date], end_date: Optional[date], changed_field: Optional[str], limit: int,
) -> list:
    page = get_audit_logs(
        db, keyword=keyword, username=username, action_type=action_type, menu_key=menu_key,
        target_type=target_type, access_type=access_type, start_date=start_date, end_date=end_date,
        page=1, page_size=limit + 1, changed_field=changed_field,
    )
    ids = [item.id for item in page.items]
    if not ids:
        return []
    return list(db.scalars(
        select(AuditLog).where(AuditLog.id.in_(ids))
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
    ).all())


def sanitize_audit_data(data: Optional[dict]) -> Optional[dict]:
    if data is None:
        return None
    sanitized = {}
    for raw_key, value in data.items():
        key = str(raw_key)
        normalized = key.lower().replace("-", "_").replace(" ", "_")
        if any(part in normalized for part in SENSITIVE_FIELD_PARTS):
            continue
        sanitized[key] = _json_value(value)
    return sanitized


def build_audit_changes(before_data: Optional[dict], after_data: Optional[dict], excluded_fields=None):
    has_before = before_data is not None
    has_after = after_data is not None
    before = sanitize_audit_data(before_data) or {}
    after = sanitize_audit_data(after_data) or {}
    excluded = set(excluded_fields or [])
    fields = []
    normalized_before = {}
    normalized_after = {}
    for key in sorted(set(before) | set(after)):
        if key in excluded:
            continue
        before_value = _normalize_empty(before.get(key))
        after_value = _normalize_empty(after.get(key))
        if before_value != after_value:
            fields.append(key)
            if has_before:
                normalized_before[key] = before.get(key)
            if has_after:
                normalized_after[key] = after.get(key)
    return normalized_before or None, normalized_after or None, fields


def audit_snapshot(value, fields) -> dict:
    return sanitize_audit_data({field: getattr(value, field, None) for field in fields}) or {}


def _normalize_empty(value):
    return None if value == "" else value


def _json_value(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return sanitize_audit_data(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
