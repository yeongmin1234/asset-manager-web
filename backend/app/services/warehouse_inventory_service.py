import copy
import logging
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
logger = logging.getLogger(__name__)


class WarehouseMasterUnavailableError(Exception):
    pass


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
            except (SQLAlchemyError, WarehouseMasterUnavailableError):
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
        source_rows = [{
            "warehouse_code": row.warehouse_code,
            "warehouse_name": row.warehouse_name,
        } for row in snapshots]
        cached_locations = self.inventory_service.list_cached_warehouse_locations()
        if isinstance(cached_locations, list):
            source_rows.extend(cached_locations)
        found = {}
        for row in source_rows:
            code = str(row.get("warehouse_code") or row.get("WH_CD") or row.get("LOCATION_CD") or row.get("DEPT_CD") or "").strip().upper()
            if not code or len(code) > 5 or code in found:
                continue
            name = str(row.get("warehouse_name") or row.get("WH_DES") or row.get("LOCATION_DES") or row.get("DEPT_DES") or "").strip()
            if not name:
                continue
            department_store_name = str(row.get("department_store_name") or row.get("DEPT_DES") or "").strip() or None
            branch_name = str(row.get("branch_name") or row.get("BRANCH_DES") or row.get("BRANCH_NAME") or "").strip() or None
            location_type = self._classify_location(name, row.get("source_location_type") or row.get("LOCATION_TYPE") or row.get("WH_TYPE"))
            display_name = " ".join(value for value in (department_store_name, branch_name) if value) or name
            found[code] = {
                "warehouse_code": code, "warehouse_name": name, "location_type": location_type,
                "department_store_name": department_store_name, "branch_name": branch_name,
                "display_name": display_name,
                "search_value": self._normalize_search("{} {} {} {}".format(code, name, department_store_name or "", branch_name or "")),
            }
        if source_rows and not found:
            logger.warning(
                "warehouse_master_mapping_empty source_count=%s normalized_count=0 cache_hit=false stale_used=false",
                len(source_rows),
            )
            raise WarehouseMasterUnavailableError("창고 목록 원본 필드 매핑을 확인해주세요.")
        if not found:
            logger.warning("warehouse_master_mapping_empty source_count=0 normalized_count=0 cache_hit=false stale_used=false")
            raise WarehouseMasterUnavailableError("사용 가능한 창고 목록 원본이 없습니다.")
        return sorted(found.values(), key=self._warehouse_sort_key)

    @classmethod
    def _warehouse_sort_key(cls, row):
        name = str(row.get("display_name") or row.get("warehouse_name") or "")
        compact = cls._normalize_search(name)
        if "파주" in compact:
            exact_rank = 0 if compact == "파주창고" else 1 if compact == "파주rma" else 2 if compact == "파주as창고" else 3
            return (0, exact_rank, name.casefold(), row["warehouse_code"])
        if row.get("location_type") == "department_store":
            return (1, 0, name.casefold(), row["warehouse_code"])
        if row.get("location_type") == "warehouse":
            return (2, 0, name.casefold(), row["warehouse_code"])
        return (3, 0, name.casefold(), row["warehouse_code"])

    @staticmethod
    def _classify_location(name, raw_type=None):
        normalized_type = str(raw_type or "").strip().casefold()
        if normalized_type in {"department_store", "department", "dept", "백화점"}:
            return "department_store"
        if normalized_type in {"warehouse", "wh", "창고"}:
            return "warehouse"
        compact = str(name or "").replace(" ", "").casefold()
        department_tokens = ("백화점", "롯데", "현대", "신세계", "갤러리아", "ak", "nc", "아울렛")
        if any(token in compact for token in department_tokens):
            return "department_store"
        return "warehouse" if "창고" in compact or "rma" in compact else "other"

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
