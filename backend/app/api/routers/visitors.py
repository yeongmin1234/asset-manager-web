from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Depends, Request

from app.core.auth import get_current_user, require_admin
from app.models.user import User
from app.services.login_access_log_service import get_client_ip


ACTIVE_WINDOW_SECONDS = 180
_visitors: Dict[str, Dict[str, object]] = {}

router = APIRouter(prefix="/visitors", tags=["visitors"])


def _now() -> datetime:
    return datetime.utcnow()


def _get_active_visitors() -> List[dict]:
    cutoff = _now() - timedelta(seconds=ACTIVE_WINDOW_SECONDS)
    stale_ips = []
    active_visitors = []

    for ip_address, visitor in _visitors.items():
        last_seen = visitor.get("last_seen")
        if not isinstance(last_seen, datetime) or last_seen < cutoff:
            stale_ips.append(ip_address)
            continue
        active_visitors.append(
            {
                "ip_address": ip_address,
                "last_seen": last_seen.isoformat(timespec="seconds"),
                "user_agent": visitor.get("user_agent") or "",
                "user_id": visitor.get("user_id"),
                "username": visitor.get("username") or None,
                "user_name": visitor.get("user_name") or None,
            }
        )

    for ip_address in stale_ips:
        _visitors.pop(ip_address, None)

    active_visitors.sort(key=lambda item: item["last_seen"], reverse=True)
    return active_visitors


@router.post("/ping")
def ping_visitor(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    client_host = get_client_ip(request) or "unknown"
    _visitors[client_host] = {
        "last_seen": _now(),
        "user_agent": request.headers.get("user-agent", ""),
        "user_id": current_user.id,
        "username": current_user.username,
        "user_name": current_user.name,
    }
    return {"ok": True}


@router.get("/summary")
def read_visitor_summary(_: User = Depends(require_admin)) -> dict:
    visitors = _get_active_visitors()
    return {
        "active_count": len(visitors),
        "active_window_seconds": ACTIVE_WINDOW_SECONDS,
        "visitors": visitors,
    }
