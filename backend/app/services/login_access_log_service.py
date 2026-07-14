import ipaddress
import logging
import math
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.login_access_log import LoginAccessLog
from app.schemas.login_access_log import LoginAccessLogPage


logger = logging.getLogger(__name__)
INTERNAL_NETWORKS = (
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)


def record_access_log(
    db: Session,
    request: Request,
    *,
    username: str,
    event_type: str,
    login_result: str,
    user_id: Optional[int] = None,
    user_name: Optional[str] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """Best-effort authentication log. A failure must never block authentication."""
    try:
        ip_address = get_client_ip(request)
        user_agent = (request.headers.get("user-agent") or "").strip() or None
        browser, operating_system = parse_user_agent(user_agent)
        db.add(LoginAccessLog(
            user_id=user_id,
            username=(username or "").strip()[:80],
            user_name=(user_name or "").strip()[:100] or None,
            event_type=event_type,
            login_result=login_result,
            ip_address=ip_address,
            access_type=classify_access_type(ip_address),
            user_agent=user_agent,
            browser=browser,
            operating_system=operating_system,
            failure_reason=failure_reason,
        ))
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to record login access log")


def get_access_logs(
    db: Session,
    *,
    keyword: Optional[str],
    username: Optional[str],
    event_type: Optional[str],
    login_result: Optional[str],
    access_type: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    page: int,
    page_size: int,
) -> LoginAccessLogPage:
    conditions = []
    if keyword and keyword.strip():
        pattern = "%{}%".format(keyword.strip())
        conditions.append(or_(
            LoginAccessLog.username.ilike(pattern),
            LoginAccessLog.user_name.ilike(pattern),
            LoginAccessLog.ip_address.ilike(pattern),
            LoginAccessLog.browser.ilike(pattern),
            LoginAccessLog.operating_system.ilike(pattern),
        ))
    if username and username.strip():
        conditions.append(LoginAccessLog.username.ilike("%{}%".format(username.strip())))
    if event_type:
        conditions.append(LoginAccessLog.event_type == event_type)
    if login_result:
        conditions.append(LoginAccessLog.login_result == login_result)
    if access_type:
        conditions.append(LoginAccessLog.access_type == access_type)
    if start_date:
        conditions.append(LoginAccessLog.occurred_at >= datetime.combine(start_date, time.min))
    if end_date:
        conditions.append(LoginAccessLog.occurred_at < datetime.combine(end_date + timedelta(days=1), time.min))

    filtered = select(LoginAccessLog).where(*conditions)
    total = int(db.scalar(select(func.count()).select_from(filtered.subquery())) or 0)
    items = list(db.scalars(
        filtered.order_by(LoginAccessLog.occurred_at.desc(), LoginAccessLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    return LoginAccessLogPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, int(math.ceil(total / float(page_size)))),
    )


def get_client_ip(request: Request) -> Optional[str]:
    direct_ip = request.client.host if request.client else None
    if direct_ip and direct_ip in settings.trusted_proxy_ip_list:
        forwarded = request.headers.get("x-forwarded-for", "")
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate and _is_valid_ip(candidate):
            return candidate
    return direct_ip


def classify_access_type(ip_address: Optional[str]) -> str:
    if not ip_address:
        return "external"
    try:
        address = ipaddress.ip_address(ip_address)
        return "internal" if any(address in network for network in INTERNAL_NETWORKS if address.version == network.version) else "external"
    except ValueError:
        return "external"


def parse_user_agent(user_agent: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not user_agent:
        return None, None
    value = user_agent.lower()
    if "edg/" in value or "edge/" in value:
        browser = "Edge"
    elif "opr/" in value or "opera" in value:
        browser = "Opera"
    elif "firefox/" in value:
        browser = "Firefox"
    elif "chrome/" in value or "crios/" in value:
        browser = "Chrome"
    elif "safari/" in value:
        browser = "Safari"
    else:
        browser = "기타"

    if "windows" in value:
        operating_system = "Windows"
    elif "android" in value:
        operating_system = "Android"
    elif "iphone" in value or "ipad" in value or "ios" in value:
        operating_system = "iOS"
    elif "mac os" in value or "macintosh" in value:
        operating_system = "macOS"
    elif "linux" in value:
        operating_system = "Linux"
    else:
        operating_system = "기타"
    return browser, operating_system


def _is_valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
