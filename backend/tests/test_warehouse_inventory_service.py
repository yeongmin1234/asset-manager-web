import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.inventory_service import InventoryRateLimitError
from app.services.warehouse_inventory_service import WarehouseInventoryService, clear_warehouse_caches
import app.services.warehouse_inventory_service as warehouse_module
from sqlalchemy.exc import OperationalError


class ScalarResult:
    def __init__(self, rows): self.rows = rows
    def scalars(self): return self
    def all(self): return self.rows


class WarehouseInventoryServiceTest(unittest.TestCase):
    def setUp(self): clear_warehouse_caches()
    def tearDown(self): clear_warehouse_caches()

    @staticmethod
    def snapshots():
        return [
            SimpleNamespace(warehouse_code="00001", warehouse_name="파주창고"),
            SimpleNamespace(warehouse_code="D001", warehouse_name="롯데백화점 본점"),
            SimpleNamespace(warehouse_code="00001", warehouse_name="이전 이름"),
        ]

    def test_warehouse_list_search_paging_cache_and_department_store_type(self):
        db = Mock(); db.execute.return_value = ScalarResult(self.snapshots())
        service = WarehouseInventoryService(db=db, inventory_service=Mock())
        first = service.list_warehouses(keyword="백화점", limit=1, offset=0)
        second = service.list_warehouses(limit=50)
        self.assertEqual(first["items"][0]["warehouse_code"], "D001")
        self.assertEqual(first["items"][0]["location_type"], "department_store")
        self.assertEqual(second["total"], 2)
        db.execute.assert_called_once()

    def test_opening_warehouse_list_does_not_call_inventory_api(self):
        db = Mock(); db.execute.return_value = ScalarResult(self.snapshots())
        inventory = Mock()
        WarehouseInventoryService(db=db, inventory_service=inventory).list_warehouses()
        inventory.get_inventory_by_location.assert_not_called()

    def test_warehouse_list_uses_stale_fallback_on_database_failure(self):
        db = Mock(); db.execute.return_value = ScalarResult(self.snapshots())
        service = WarehouseInventoryService(db=db, inventory_service=Mock())
        service.list_warehouses()
        _, stale_until, rows = warehouse_module._warehouse_list_cache
        warehouse_module._warehouse_list_cache = (time.monotonic() - 1, stale_until, rows)
        db.execute.side_effect = OperationalError("select", {}, Exception("offline"))
        result = service.list_warehouses()
        self.assertEqual(result["cache_status"], "stale")

    def test_selected_warehouse_calls_one_code_and_filters_sorts_locally(self):
        inventory = Mock()
        inventory.get_inventory_by_location.return_value = [
            {"item_code": "A", "item_name": "랜턴", "product_size_description": None, "unit": "EA", "quantity": "2.5", "warehouse_name": "파주창고"},
            {"item_code": "B", "item_name": "토스터", "product_size_description": None, "unit": "EA", "quantity": "0", "warehouse_name": "파주창고"},
            {"item_code": "C", "item_name": "기타", "product_size_description": None, "unit": "EA", "quantity": "-1", "warehouse_name": "파주창고"},
        ]
        service = WarehouseInventoryService(inventory_service=inventory)
        result = service.get_warehouse_inventory("00001")
        included = service.get_warehouse_inventory("00001", keyword="토스터", include_zero=True, sort="quantity_asc")
        self.assertEqual([row["item_code"] for row in result["items"]], ["A", "C"])
        self.assertEqual(included["items"][0]["item_code"], "B")
        inventory.get_inventory_by_location.assert_called_once_with(warehouse_code="00001", limit=200)

    def test_same_warehouse_requests_are_single_flight_and_cached(self):
        inventory = Mock(); calls = []
        def load(**kwargs):
            calls.append(kwargs["warehouse_code"]); time.sleep(0.03); return []
        inventory.get_inventory_by_location.side_effect = load
        service = WarehouseInventoryService(inventory_service=inventory)
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(lambda _: service.get_warehouse_inventory("00001"), range(2)))
        self.assertEqual(calls, ["00001"])

    def test_rate_limit_is_preserved_and_not_cached(self):
        inventory = Mock()
        inventory.get_inventory_by_location.side_effect = InventoryRateLimitError("rate_limited", "safe", 412, retry_after_seconds=30)
        with self.assertRaises(InventoryRateLimitError):
            WarehouseInventoryService(inventory_service=inventory).get_warehouse_inventory("00001")


if __name__ == "__main__": unittest.main()
