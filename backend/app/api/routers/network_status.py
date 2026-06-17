from datetime import datetime
from time import perf_counter
from typing import Any, Dict, List
import socket
from urllib import request
from urllib.error import HTTPError, URLError

from fastapi import APIRouter


ROUTER_IP = "192.168.222.1"
NAS_IP = "192.168.222.210"
CHECK_TIMEOUT_SECONDS = 2.0
SLOW_RESPONSE_MS = 1500

CHECK_TARGETS = [
    {
        "name": "ASUS 공유기",
        "target": "{}:53".format(ROUTER_IP),
        "type": "tcp",
        "host": ROUTER_IP,
        "port": 53,
    },
    {
        "name": "인터넷 연결",
        "target": "1.1.1.1:53",
        "type": "tcp",
        "host": "1.1.1.1",
        "port": 53,
    },
    {
        "name": "NAS",
        "target": "{}:8010".format(NAS_IP),
        "type": "tcp",
        "host": NAS_IP,
        "port": 8010,
    },
    {
        "name": "Frontend",
        "target": "http://127.0.0.1:3010",
        "type": "http",
        "url": "http://127.0.0.1:3010",
    },
    {
        "name": "Backend API",
        "target": "http://127.0.0.1:8010/health",
        "type": "http",
        "url": "http://127.0.0.1:8010/health",
    },
    {
        "name": "Database",
        "target": "http://127.0.0.1:8010/health/db",
        "type": "http",
        "url": "http://127.0.0.1:8010/health/db",
    },
    {
        "name": "PostgreSQL TCP",
        "target": "127.0.0.1:15432",
        "type": "tcp",
        "host": "127.0.0.1",
        "port": 15432,
    },
]


router = APIRouter(prefix="/network", tags=["network"])


@router.get("/status")
def get_network_status() -> Dict[str, Any]:
    items = [check_target(target) for target in CHECK_TARGETS]
    return {
        "items": items,
        "summary": build_summary(items),
    }


def check_target(target: Dict[str, Any]) -> Dict[str, Any]:
    checked_at = datetime.utcnow().isoformat()
    started_at = perf_counter()

    try:
        if target["type"] == "http":
            status = check_http_target(str(target["url"]))
        else:
            status = check_tcp_target(str(target["host"]), int(target["port"]))
    except Exception:
        status = "down"

    latency_ms = int(round((perf_counter() - started_at) * 1000))
    if status == "ok" and latency_ms >= SLOW_RESPONSE_MS:
        status = "warning"

    return {
        "name": target["name"],
        "target": target["target"],
        "type": target["type"],
        "status": status,
        "latency_ms": latency_ms,
        "checked_at": checked_at,
    }


def check_tcp_target(host: str, port: int) -> str:
    with socket.create_connection((host, port), timeout=CHECK_TIMEOUT_SECONDS):
        return "ok"


def check_http_target(url: str) -> str:
    http_request = request.Request(url, headers={"User-Agent": "asset-manager-network-status"})
    try:
        with request.urlopen(http_request, timeout=CHECK_TIMEOUT_SECONDS) as response:
            status_code = int(getattr(response, "status", response.getcode()))
    except HTTPError as exc:
        status_code = int(exc.code)
    except (TimeoutError, URLError, socket.timeout):
        return "down"

    return "ok" if status_code < 400 else "warning"


def build_summary(items: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {
        "total": len(items),
        "ok": 0,
        "warning": 0,
        "down": 0,
    }

    for item in items:
        status = str(item.get("status") or "down")
        if status in summary:
            summary[status] += 1
        else:
            summary["down"] += 1

    return summary
