import copy
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


CONTEXT_TTL_SECONDS = 30 * 60
MAX_CONTEXT_USERS = 1000
MAX_CLIENT_CONTEXT_BYTES = 32 * 1024
MAX_CONTEXT_WAREHOUSES = 200
MAX_CONTEXT_CANDIDATES = 8


@dataclass
class InventoryContext:
    last_intent: str
    last_query: str
    last_item_code: Optional[str]
    last_item_name: Optional[str]
    last_inventory_items: List[Dict[str, Any]]
    last_selected_item: Optional[Dict[str, Any]]
    last_threshold: Optional[int]
    last_searched_at: Optional[str]
    last_accessed_at: float


_contexts: Dict[int, InventoryContext] = {}
_context_lock = threading.Lock()


def save_inventory_context(
    user_id: int,
    intent: str,
    query: str,
    items: List[Dict[str, Any]],
    threshold: Optional[int] = None,
    searched_at: Optional[str] = None,
    selected_item_code: Optional[str] = None,
) -> InventoryContext:
    safe_items = [_sanitize_item(item) for item in items]
    selected = next(
        (item for item in safe_items if item["item_code"] == selected_item_code),
        safe_items[0] if safe_items else None,
    )
    context = InventoryContext(
        last_intent=intent,
        last_query=(query or "").strip(),
        last_item_code=selected["item_code"] if selected else None,
        last_item_name=selected["item_name"] if selected else None,
        last_inventory_items=safe_items,
        last_selected_item=selected,
        last_threshold=threshold,
        last_searched_at=searched_at,
        last_accessed_at=time.monotonic(),
    )
    with _context_lock:
        _remove_expired_locked()
        if int(user_id) not in _contexts and len(_contexts) >= MAX_CONTEXT_USERS:
            oldest_user_id = min(_contexts, key=lambda key: _contexts[key].last_accessed_at)
            _contexts.pop(oldest_user_id, None)
        _contexts[int(user_id)] = context
    return copy.deepcopy(context)


def get_inventory_context(user_id: int) -> Optional[InventoryContext]:
    with _context_lock:
        _remove_expired_locked()
        context = _contexts.get(int(user_id))
        if context is None:
            return None
        context.last_accessed_at = time.monotonic()
        return copy.deepcopy(context)


def select_context_item(user_id: int, item: Dict[str, Any]) -> None:
    with _context_lock:
        context = _contexts.get(int(user_id))
        if context is None:
            return
        selected = _sanitize_item(item)
        context.last_selected_item = selected
        context.last_item_code = selected["item_code"]
        context.last_item_name = selected["item_name"]
        context.last_accessed_at = time.monotonic()


def clear_inventory_contexts() -> None:
    with _context_lock:
        _contexts.clear()


def expire_inventory_context_for_test(user_id: int) -> None:
    with _context_lock:
        if int(user_id) in _contexts:
            _contexts[int(user_id)].last_accessed_at -= CONTEXT_TTL_SECONDS + 1


def classify_inventory_followup(message: str) -> Optional[str]:
    normalized = re.sub(r"\s+", " ", (message or "").strip().lower())
    if any(phrase in normalized for phrase in ("지금 다시", "최신 재고", "최신 재고로", "현재 기준으로 다시", "다시 조회", "새로 조회", "재고 다시 확인")):
        return "inventory_refresh"
    if any(phrase in normalized for phrase in ("새 질문할게", "처음부터", "이전 내용 지워줘", "대화 초기화")):
        return "context_clear"
    if any(phrase in normalized for phrase in ("다른 창고", "나머지 창고")):
        return "inventory_other_warehouses"
    if any(phrase in normalized for phrase in ("전체 창고", "모든 창고", "자세히 보여줘")):
        return "inventory_show_all_warehouses"
    if any(phrase in normalized for phrase in ("품목코드 알려", "품목 코드는", "품목코드는", "그 품목 코드", "코드가 뭐")):
        return "inventory_item_code_followup"
    if any(phrase in normalized for phrase in ("품목명 알려", "품목명은", "이름은", "이름이 뭐")):
        return "inventory_item_name_followup"
    if any(phrase in normalized for phrase in ("규격 알려", "규격은")):
        return "inventory_size_followup"
    if any(phrase in normalized for phrase in ("단위 알려", "단위는")):
        return "inventory_unit_followup"
    if any(phrase in normalized for phrase in ("어느 창고", "창고별로", "어디에 있어", "창고 재고")):
        return "inventory_context_warehouses"
    if any(phrase in normalized for phrase in ("총 몇 개", "전체 재고", "몇 개라고 했지", "총재고 다시")):
        return "inventory_total_followup"
    if any(phrase in normalized for phrase in ("아까 그 품목", "방금 조회한 품목", "이 품목 재고")):
        return "inventory_context_recent"
    if "첫 번째 품목" in normalized:
        return "inventory_context_first"
    if "두 번째 품목" in normalized:
        return "inventory_context_second"
    if "가장 재고가 적은 품목" in normalized:
        return "inventory_context_lowest"
    if re.fullmatch(r"[가-힣a-z0-9._-]+(?:\s*(?:관련\s*)?창고)?만(?:\s*(?:보여줘|알려줘|조회해줘))?", normalized):
        return "inventory_warehouse_filter"
    return None


def sanitize_client_context(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("이전 조회 정보를 확인할 수 없습니다. 품목을 다시 조회해주세요.")
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        raise ValueError("이전 조회 정보를 확인할 수 없습니다. 품목을 다시 조회해주세요.")
    if len(encoded) > MAX_CLIENT_CONTEXT_BYTES:
        raise ValueError("이전 조회 정보가 너무 큽니다. 품목을 다시 조회해주세요.")
    inventory = value.get("inventory_result")
    if inventory is not None and not isinstance(inventory, dict):
        raise ValueError("이전 조회 정보를 확인할 수 없습니다. 품목을 다시 조회해주세요.")
    warehouses = inventory.get("warehouses") if inventory else []
    if not isinstance(warehouses, list) or len(warehouses) > MAX_CONTEXT_WAREHOUSES:
        raise ValueError("이전 조회 정보를 확인할 수 없습니다. 품목을 다시 조회해주세요.")
    safe_warehouses = [_sanitize_warehouse(row) for row in warehouses if isinstance(row, dict)]
    candidates = value.get("product_candidates") or []
    if not isinstance(candidates, list):
        raise ValueError("이전 조회 정보를 확인할 수 없습니다. 품목을 다시 조회해주세요.")
    return {
        "selected_item_code": _short(value.get("selected_item_code"), 80),
        "selected_item_name": _short(value.get("selected_item_name"), 160),
        "unit": _short(value.get("unit"), 40),
        "size": _short(value.get("size"), 160),
        "last_intent": _short(value.get("last_intent"), 80),
        "searched_at": _short(value.get("searched_at"), 80),
        "last_warehouse_filter": _short(value.get("last_warehouse_filter"), 160),
        "search_keyword": _short(value.get("search_keyword"), 160),
        "product_candidates": [_sanitize_candidate(row) for row in candidates[:MAX_CONTEXT_CANDIDATES] if isinstance(row, dict)],
        "inventory_result": {
            "total_quantity": _short(inventory.get("total_quantity"), 80) if inventory else None,
            "warehouses": safe_warehouses,
        } if inventory else None,
    }


def context_from_item(item: Dict[str, Any], intent: str, searched_at: Optional[str] = None) -> Dict[str, Any]:
    safe = _sanitize_item(item)
    return {
        "selected_item_code": safe["item_code"], "selected_item_name": safe["item_name"],
        "unit": safe["unit"], "size": safe["size"], "last_intent": intent,
        "searched_at": searched_at, "last_warehouse_filter": None,
        "search_keyword": None, "product_candidates": [],
        "inventory_result": {"total_quantity": safe["total_quantity"], "warehouses": safe["warehouses"]},
    }


def _short(value: Any, limit: int) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip()[:limit] or None


def _sanitize_warehouse(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"warehouse_code": _short(row.get("warehouse_code"), 80), "warehouse_name": _short(row.get("warehouse_name"), 160), "quantity": _short(row.get("quantity"), 80) or "0"}


def _sanitize_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    return {"item_code": _short(row.get("item_code"), 80), "item_name": _short(row.get("item_name"), 160), "unit": _short(row.get("unit"), 40), "size": _short(row.get("size"), 160)}


def _remove_expired_locked() -> None:
    now = time.monotonic()
    expired = [key for key, value in _contexts.items() if now - value.last_accessed_at > CONTEXT_TTL_SECONDS]
    for key in expired:
        _contexts.pop(key, None)


def _sanitize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    warehouses = [
        {
            "warehouse_code": warehouse.get("warehouse_code"),
            "warehouse_name": warehouse.get("warehouse_name"),
            "quantity": str(warehouse.get("quantity", "")),
        }
        for warehouse in (item.get("warehouses") or [])
        if isinstance(warehouse, dict)
    ]
    return {
        "item_code": str(item.get("item_code") or "").strip().upper(),
        "item_name": item.get("item_name"),
        "size": item.get("size"),
        "unit": item.get("unit"),
        "total_quantity": str(item.get("total_quantity", "")),
        "warehouses": warehouses,
    }
