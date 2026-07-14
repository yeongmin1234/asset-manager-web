import logging
import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Optional, Any

from fastapi import Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.menu_access_log import MenuAccessLog
from app.models.user import User
from app.schemas.menu_access_log import (
    MenuAccessLogCreate,
    MenuAccessLogCreateResponse,
    MenuAccessLogPage,
)
from app.services.login_access_log_service import (
    classify_access_type, get_client_ip, parse_user_agent,
)


logger = logging.getLogger(__name__)
MENU_ACCESS_TARGETS: Dict[str, Dict[str, Any]] = {
    "dashboard": {"name": "대시보드", "path": "/dashboard", "permission": "dashboard", "admin": None},
    "drink_orders": {"name": "음료주문기록", "path": "/beverage-orders", "permission": "drink_orders", "admin": None},
    "vendor_contacts": {"name": "업체연락처", "path": "/vendor-contacts", "permission": "vendor_contacts", "admin": None},
    "expiration_schedules": {"name": "점검·만료 관리", "path": "/expiration-schedules", "permission": "expiration_schedules", "admin": None},
    "assets": {"name": "자산 관리", "path": "/assets", "permission": "assets", "admin": None},
    "software": {"name": "SW 현황", "path": "/software", "permission": "software", "admin": None},
    "company_cars": {"name": "법인차량 관리", "path": "/vehicles", "permission": "company_cars", "admin": None},
    "fire_insurance": {"name": "파주화재보험", "path": "/paju-fire-insurance", "permission": "fire_insurance", "admin": None},
    "access_info": {"name": "접속정보 관리", "path": "/access-info", "permission": "access_info", "admin": None},
    "equipment_status": {"name": "장비 현황", "path": "/equipment-status", "permission": "equipment_status", "admin": None},
    "excel_management": {"name": "엑셀 관리", "path": "/excel", "permission": None, "admin": True},
    "statistics": {"name": "통계 / 리포트", "path": "/statistics", "permission": "statistics", "admin": None},
    "scm": {"name": "SCM", "path": "/scm", "permission": None, "admin": True},
    "user_management": {"name": "사용자 관리", "path": "/admin/users", "permission": None, "admin": True},
    "hr_list": {"name": "인사업무 > 리스트", "path": "/hr/list", "permission": "hr_list", "admin": None},
    "history": {"name": "변경 이력", "path": "/history", "permission": "changelog", "admin": None},
    "settings": {"name": "설정", "path": "/settings", "permission": None, "admin": True},
    "work_manual": {"name": "업무설명서", "path": "/work-manuals", "permission": "work_manual", "admin": None},
    "install_files": {"name": "설치자료실", "path": "/install-library", "permission": None, "admin": True},
    "excel_import": {"name": "엑셀 일괄등록", "path": "/hr/list", "permission": None, "admin": True},
}
MENU_ACCESS_DEDUPLICATION_MINUTES = 5


class MenuAccessDeniedError(Exception):
    pass


class MenuAccessPayloadError(Exception):
    pass


def record_menu_access_log(
    db: Session,
    request: Request,
    user: User,
    payload: MenuAccessLogCreate,
) -> MenuAccessLogCreateResponse:
    target = MENU_ACCESS_TARGETS[payload.menu_key]
    _validate_menu_access(user, payload, target)
    try:
        latest = db.scalar(
            select(MenuAccessLog)
            .where(MenuAccessLog.user_id == user.id)
            .order_by(MenuAccessLog.occurred_at.desc(), MenuAccessLog.id.desc())
            .limit(1)
        )
        threshold = datetime.now(timezone.utc) - timedelta(minutes=MENU_ACCESS_DEDUPLICATION_MINUTES)
        if latest and latest.menu_key == payload.menu_key and _is_recent(latest.occurred_at, threshold):
            return MenuAccessLogCreateResponse(recorded=False, deduplicated=True)

        ip_address = get_client_ip(request)
        user_agent = (request.headers.get("user-agent") or "").strip() or None
        browser, operating_system = parse_user_agent(user_agent)
        db.add(MenuAccessLog(
            user_id=user.id,
            username=user.username,
            user_name=user.name,
            menu_key=payload.menu_key,
            menu_name=str(target["name"]),
            route_path=str(target["path"]),
            ip_address=ip_address,
            access_type=classify_access_type(ip_address),
            user_agent=user_agent,
            browser=browser,
            operating_system=operating_system,
        ))
        db.commit()
        return MenuAccessLogCreateResponse(recorded=True, deduplicated=False)
    except Exception:
        db.rollback()
        logger.exception("Failed to record menu access log")
        return MenuAccessLogCreateResponse(recorded=False, deduplicated=False)


def get_menu_access_logs(
    db: Session,
    *,
    keyword: Optional[str],
    username: Optional[str],
    menu_key: Optional[str],
    access_type: Optional[str],
    start_date: Optional[date],
    end_date: Optional[date],
    page: int,
    page_size: int,
) -> MenuAccessLogPage:
    conditions = []
    if keyword and keyword.strip():
        pattern = "%{}%".format(keyword.strip())
        conditions.append(or_(
            MenuAccessLog.username.ilike(pattern),
            MenuAccessLog.user_name.ilike(pattern),
            MenuAccessLog.ip_address.ilike(pattern),
            MenuAccessLog.menu_name.ilike(pattern),
            MenuAccessLog.route_path.ilike(pattern),
        ))
    if username and username.strip():
        conditions.append(or_(
            MenuAccessLog.username.ilike("%{}%".format(username.strip())),
            MenuAccessLog.user_name.ilike("%{}%".format(username.strip())),
        ))
    if menu_key:
        conditions.append(MenuAccessLog.menu_key == menu_key)
    if access_type:
        conditions.append(MenuAccessLog.access_type == access_type)
    if start_date:
        conditions.append(MenuAccessLog.occurred_at >= datetime.combine(start_date, time.min))
    if end_date:
        conditions.append(MenuAccessLog.occurred_at < datetime.combine(end_date + timedelta(days=1), time.min))

    filtered = select(MenuAccessLog).where(*conditions)
    total = int(db.scalar(select(func.count()).select_from(filtered.subquery())) or 0)
    items = list(db.scalars(
        filtered.order_by(MenuAccessLog.occurred_at.desc(), MenuAccessLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all())
    menu_options = [
        {"menu_key": row[0], "menu_name": row[1]}
        for row in db.execute(
            select(MenuAccessLog.menu_key, MenuAccessLog.menu_name)
            .distinct()
            .order_by(MenuAccessLog.menu_name.asc())
        ).all()
    ]
    return MenuAccessLogPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, int(math.ceil(total / float(page_size)))),
        menu_options=menu_options,
    )


def _validate_menu_access(user: User, payload: MenuAccessLogCreate, target: Dict[str, Any]) -> None:
    if payload.menu_name != target["name"] or payload.route_path != target["path"]:
        raise MenuAccessPayloadError()
    if user.role == "admin":
        return
    if target.get("admin") or target.get("permission") not in set(user.menu_permissions or []):
        raise MenuAccessDeniedError()


def _is_recent(value: datetime, threshold: datetime) -> bool:
    if value.tzinfo is None:
        return value >= threshold.replace(tzinfo=None)
    return value >= threshold
