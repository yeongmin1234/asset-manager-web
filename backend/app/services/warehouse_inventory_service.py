import copy
import threading
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.inventory_snapshot import InventorySnapshot
from app.services.inventory_service import InventoryService


WAREHOUSE_LIST_CACHE_TTL_SECONDS = 3600.0
WAREHOUSE_LIST_STALE_TTL_SECONDS = 86400.0
WAREHOUSE_INVENTORY_CACHE_TTL_SECONDS = 600.0
MAX_WAREHOUSE_INVENTORY_ROWS = 200

_warehouse_list_cache: Optional[Tuple[float, float, List[Dict[str, Any]]]] = None
_warehouse_inventory_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_warehouse_list_lock = threading.Lock()
_warehouse_inventory_locks: Dict[str, threading.Lock] = {}
_warehouse_inventory_locks_guard = threading.Lock()


class WarehouseInventoryService:
    def __init__(self, db=None, inventory_service=None):
        self.db = db
        self.inventory_service = inventory_service or InventoryService()

    def list_warehouses(self, keyword: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        if limit < 1 or limit > 100:
            raise ValueError("조회 건수는 1건 이상 100건 이하로 입력해주세요.")
        if offset < 0:
            raise ValueError("조회 시작 위치는 0 이상이어야 합니다.")
        warehouses, cache_status = self._get_warehouses()
        normalized = self._normalize_search(keyword)
        if normalized:
            warehouses = [row for row in warehouses if normalized in row["search_value"]]
        total = len(warehouses)
        items = [{key: value for key, value in row.items() if key != "search_value"} for row in warehouses[offset:offset + limit]]
        return {"success": True, "total": total, "limit": limit, "offset": offset, "items": items, "cache_status": cache_status, "data_source": "inventory_snapshots"}

    def get_warehouse_inventory(
        self, warehouse_code: str, keyword: Optional[str] = None, include_zero: bool = False,
        sort: str = "quantity_desc", limit: int = 50, offset: int = 0,
    ) -> Dict[str, Any]:
        code = str(warehouse_code or "").strip().upper()
        if not code or len(code) > 5:
            raise ValueError("창고코드를 확인해주세요.")
        if limit < 1 or limit > 100 or offset < 0:
            raise ValueError("조회 범위를 확인해주세요.")
        if sort not in {"quantity_desc", "quantity_asc", "name_asc", "name_desc"}:
            raise ValueError("정렬 조건을 확인해주세요.")
        rows, cache_hit = self._get_inventory_rows(code)
        warehouse_name = next((row.get("warehouse_name") for row in rows if row.get("warehouse_name")), code)
        positive_count = sum(1 for row in rows if self._quantity(row) > 0)
        zero_count = sum(1 for row in rows if self._quantity(row) == 0)
        negative_count = sum(1 for row in rows if self._quantity(row) < 0)
        normalized = self._normalize_search(keyword)
        filtered = [row for row in rows if (include_zero or self._quantity(row) != 0) and (
            not normalized or normalized in self._normalize_search("{} {}".format(row.get("item_name") or "", row.get("item_code") or ""))
        )]
        if sort.startswith("quantity"):
            filtered.sort(key=self._quantity, reverse=sort == "quantity_desc")
        else:
            filtered.sort(key=lambda row: str(row.get("item_name") or row.get("item_code") or "").casefold(), reverse=sort == "name_desc")
        total = len(filtered)
        return {
            "success": True, "warehouse_code": code, "warehouse_name": warehouse_name,
            "summary": {"item_count": len(rows), "positive_item_count": positive_count, "zero_item_count": zero_count, "negative_item_count": negative_count},
            "total": total, "limit": limit, "offset": offset, "items": filtered[offset:offset + limit],
            "include_zero": include_zero, "sort": sort, "cache_hit": cache_hit,
        }

    def _get_warehouses(self):
        global _warehouse_list_cache
        now = time.monotonic()
        with _warehouse_list_lock:
            cached = _warehouse_list_cache
            if cached and cached[0] > now:
                return copy.deepcopy(cached[2]), "fresh"
            stale = cached if cached and cached[1] > now else None
            try:
                rows = self._load_warehouses()
            except SQLAlchemyError:
                if stale:
                    return copy.deepcopy(stale[2]), "stale"
                raise
            _warehouse_list_cache = (now + WAREHOUSE_LIST_CACHE_TTL_SECONDS, now + WAREHOUSE_LIST_STALE_TTL_SECONDS, copy.deepcopy(rows))
            return rows, "refreshed"

    def _load_warehouses(self):
        if self.db is None:
            raise ValueError("창고 목록 데이터베이스 연결을 확인해주세요.")
        statement = select(InventorySnapshot).where(
            InventorySnapshot.row_type == "warehouse", InventorySnapshot.warehouse_code != "",
        ).order_by(InventorySnapshot.snapshot_at.desc())
        snapshots = self.db.execute(statement).scalars().all()
        found = {}
        for row in snapshots:
            code = str(row.warehouse_code or "").strip().upper()
            if not code or len(code) > 5 or code in found:
                continue
            name = str(row.warehouse_name or code).strip()
            location_type = "department_store" if "백화점" in name else "warehouse"
            found[code] = {"warehouse_code": code, "warehouse_name": name, "location_type": location_type, "search_value": self._normalize_search("{} {}".format(code, name))}
        return sorted(found.values(), key=lambda row: (row["warehouse_name"].casefold(), row["warehouse_code"]))

    def _get_inventory_rows(self, code):
        now = time.monotonic()
        cached = _warehouse_inventory_cache.get(code)
        if cached and cached[0] > now:
            return copy.deepcopy(cached[1]), True
        with _warehouse_inventory_locks_guard:
            lock = _warehouse_inventory_locks.setdefault(code, threading.Lock())
        with lock:
            cached = _warehouse_inventory_cache.get(code)
            if cached and cached[0] > time.monotonic():
                return copy.deepcopy(cached[1]), True
            locations = self.inventory_service.get_inventory_by_location(warehouse_code=code, limit=MAX_WAREHOUSE_INVENTORY_ROWS)
            rows = [{
                "item_code": row.get("item_code"), "item_name": row.get("item_name"),
                "size": row.get("product_size_description"), "unit": row.get("unit"),
                "quantity": row.get("quantity"), "warehouse_code": code,
                "warehouse_name": row.get("warehouse_name"),
            } for row in locations]
            _warehouse_inventory_cache[code] = (time.monotonic() + WAREHOUSE_INVENTORY_CACHE_TTL_SECONDS, copy.deepcopy(rows))
            return rows, False

    @staticmethod
    def _normalize_search(value):
        return "".join(str(value or "").strip().casefold().split())

    @staticmethod
    def _quantity(row):
        try:
            return Decimal(str(row.get("quantity") or "0"))
        except (InvalidOperation, ValueError):
            return Decimal("0")


def clear_warehouse_caches():
    global _warehouse_list_cache
    with _warehouse_list_lock:
        _warehouse_list_cache = None
    _warehouse_inventory_cache.clear()
