import copy
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


CONTEXT_TTL_SECONDS = 30 * 60
MAX_CONTEXT_USERS = 1000


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
    if any(phrase in normalized for phrase in ("지금 다시", "최신 재고", "현재 기준으로 다시", "다시 조회", "재고 다시 확인")):
        return "inventory_refresh"
    if any(phrase in normalized for phrase in ("어느 창고", "창고별로", "어디에 있어", "창고 재고")):
        return "inventory_context_warehouses"
    if any(phrase in normalized for phrase in ("총 몇 개", "전체 재고", "몇 개라고 했지", "총재고 다시")):
        return "inventory_context_total"
    if any(phrase in normalized for phrase in ("아까 그 품목", "방금 조회한 품목", "이 품목 재고")):
        return "inventory_context_recent"
    if "첫 번째 품목" in normalized:
        return "inventory_context_first"
    if "두 번째 품목" in normalized:
        return "inventory_context_second"
    if "가장 재고가 적은 품목" in normalized:
        return "inventory_context_lowest"
    return None


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
