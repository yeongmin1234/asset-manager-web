from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, Request


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
            }
        )

    for ip_address in stale_ips:
        _visitors.pop(ip_address, None)

    active_visitors.sort(key=lambda item: item["last_seen"], reverse=True)
    return active_visitors


@router.post("/ping")
def ping_visitor(request: Request) -> dict:
    client_host = request.client.host if request.client else "unknown"
    _visitors[client_host] = {
        "last_seen": _now(),
        "user_agent": request.headers.get("user-agent", ""),
    }
    return {"ok": True}


@router.get("/summary")
def read_visitor_summary() -> dict:
    visitors = _get_active_visitors()
    return {
        "active_count": len(visitors),
        "active_window_seconds": ACTIVE_WINDOW_SECONDS,
        "visitors": visitors,
    }
