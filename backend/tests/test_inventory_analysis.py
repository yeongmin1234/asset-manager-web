from decimal import Decimal
from datetime import datetime, timezone
import unittest
from unittest.mock import Mock, patch

from app.services.ai_intent_service import analyze_intent
from app.services.ai_inventory_context_service import clear_inventory_contexts, save_inventory_context
from app.services.inventory_analysis_service import (
    InventoryAnalysisService,
    InventorySnapshotUnavailableError,
)


def product(code, name):
    return {"item_code": code, "item_name": name, "size": None, "unit": "EA"}


def location(code, quantity, warehouse="본사"):
    return {
        "item_code": code,
        "item_name": code,
        "product_size_description": None,
        "warehouse_code": "001",
        "warehouse_name": warehouse,
        "quantity": Decimal(str(quantity)),
    }


class FakeInventoryService:
    def __init__(self, products=None, locations=None):
        self.products = products or []
        self.locations = locations or []
        self.product_lookup_calls = 0
        self.location_lookup_calls = 0

    def search_products_for_keywords(self, keywords, limit_per_keyword=1):
        self.product_lookup_calls += 1
        return {
            keyword: [item for item in self.products if keyword.casefold() in item["item_name"].casefold()][:limit_per_keyword]
            for keyword in keywords
        }

    def search_products(self, limit=200):
        self.product_lookup_calls += 1
        return self.products[:limit]

    def get_inventory_by_location(self, item_code=None, limit=200):
        self.location_lookup_calls += 1
        rows = self.locations if not item_code else [row for row in self.locations if row["item_code"] == item_code]
        return rows[:limit]

    @staticmethod
    def _aggregate_inventory(product_item, locations):
        return {
            "item_code": product_item["item_code"],
            "item_name": product_item["item_name"],
            "size": product_item.get("size"),
            "unit": product_item.get("unit"),
            "total_quantity": sum((row["quantity"] for row in locations), Decimal("0")),
            "warehouses": [{
                "warehouse_code": row["warehouse_code"],
                "warehouse_name": row["warehouse_name"],
                "quantity": row["quantity"],
            } for row in locations],
        }


class InventoryIntentAnalysisTest(unittest.TestCase):
    def test_compare_items_are_extracted(self):
        result = analyze_intent("뉴토스터블랙이랑 뉴토스터화이트 재고 비교해줘")
        self.assertEqual(result.intent, "inventory_compare")
        self.assertEqual(result.entities["items"], ["뉴토스터블랙", "뉴토스터화이트"])

        spaced = analyze_intent("뉴토스터블랙과 뉴토스터화이트 중 어느 게 더 많아?")
        self.assertEqual(spaced.entities["items"], ["뉴토스터블랙", "뉴토스터화이트"])

    def test_sort_directions(self):
        self.assertEqual(analyze_intent("재고가 적은 순서로 보여줘").entities["direction"], "asc")
        self.assertEqual(analyze_intent("재고가 많은 순서로 보여줘").entities["direction"], "desc")

    def test_filter_condition_extraction(self):
        below = analyze_intent("재고 5개 이하 품목 알려줘")
        above = analyze_intent("재고 20개 이상 품목 알려줘")
        self.assertEqual((below.intent, below.entities), ("inventory_low_stock", {"threshold": 5, "comparison": "이하"}))
        self.assertEqual((above.intent, above.entities), ("inventory_filter", {"threshold": "20", "comparison": "gte"}))


class InventoryAnalysisServiceTest(unittest.TestCase):
    def setUp(self):
        clear_inventory_contexts()
        self.products = [product("A", "상품 A"), product("B", "상품 B"), product("C", "상품 C")]
        self.locations = [location("A", "8.5"), location("B", "3"), location("C", "-2")]

    def tearDown(self):
        clear_inventory_contexts()

    def service(self, locations=None):
        fake = FakeInventoryService(self.products, self.locations if locations is None else locations)
        return InventoryAnalysisService(fake), fake

    def test_two_item_comparison_and_single_product_lookup(self):
        service, fake = self.service()
        result = service.analyze("inventory_compare", 1, queries=["상품 A", "상품 B"])
        self.assertEqual(result["total"], 2)
        self.assertIn("5.5개 더 많습니다", result["answer"])
        self.assertEqual(fake.product_lookup_calls, 1)
        self.assertEqual(fake.location_lookup_calls, 2)

    def test_equal_quantity_comparison(self):
        service, _ = self.service([location("A", "2"), location("B", "2")])
        result = service.analyze("inventory_compare", 1, queries=["상품 A", "상품 B"])
        self.assertIn("각각 2개로 동일", result["answer"])

    def test_three_item_comparison(self):
        service, _ = self.service()
        result = service.analyze("inventory_compare", 1, queries=["상품 A", "상품 B", "상품 C"])
        self.assertEqual(result["total"], 3)

    def test_sort_ascending_uses_decimal(self):
        service, _ = self.service()
        result = service.analyze("inventory_sort", 1, direction="asc")
        self.assertEqual([item["item_code"] for item in result["items"]], ["C", "B", "A"])

    def test_sort_descending(self):
        service, _ = self.service()
        result = service.analyze("inventory_sort", 1, direction="desc")
        self.assertEqual([item["item_code"] for item in result["items"]], ["A", "B", "C"])

    def test_zero_filter(self):
        service, _ = self.service([location("A", "0"), location("B", "1")])
        result = service.analyze("inventory_zero", 1)
        self.assertEqual([item["item_code"] for item in result["items"]], ["A", "C"])

    def test_product_without_location_is_zero_stock(self):
        service, _ = self.service([location("A", "1"), location("B", "2")])
        result = service.analyze("inventory_zero", 1)
        self.assertEqual([item["item_code"] for item in result["items"]], ["C"])

    def test_negative_filter_preserves_negative(self):
        service, _ = self.service()
        result = service.analyze("inventory_negative", 1)
        self.assertEqual(result["items"][0]["total_quantity"], Decimal("-2"))

    def test_less_than_or_equal_filter(self):
        service, _ = self.service()
        result = service.analyze("inventory_filter", 1, comparison="lte", threshold="3")
        self.assertEqual([item["item_code"] for item in result["items"]], ["B", "C"])

    def test_greater_than_or_equal_filter(self):
        service, _ = self.service()
        result = service.analyze("inventory_filter", 1, comparison="gte", threshold="3")
        self.assertEqual([item["item_code"] for item in result["items"]], ["A", "B"])

    def test_maximum_and_minimum(self):
        service, _ = self.service()
        maximum = service.analyze("inventory_max", 1)
        minimum = service.analyze("inventory_min", 1)
        self.assertEqual(maximum["items"][0]["item_code"], "A")
        self.assertEqual(minimum["items"][0]["item_code"], "C")

    def test_ties_are_all_returned(self):
        service, _ = self.service([location("A", "5"), location("B", "5"), location("C", "1")])
        result = service.analyze("inventory_max", 1)
        self.assertEqual([item["item_code"] for item in result["items"]], ["A", "B"])

    def test_recent_context_can_compare_without_api_lookup(self):
        items = [
            {**product("A", "상품 A"), "total_quantity": "8", "warehouses": []},
            {**product("B", "상품 B"), "total_quantity": "3", "warehouses": []},
        ]
        save_inventory_context(1, "inventory_search", "검색", items)
        service, fake = self.service()
        result = service.analyze("inventory_compare", 1, queries=[])
        self.assertEqual(result["total"], 2)
        self.assertEqual(fake.product_lookup_calls, 0)
        self.assertEqual(fake.location_lookup_calls, 0)

    def test_low_stock_uses_latest_snapshot_without_external_lookup(self):
        service, fake = self.service()
        service.db = Mock()
        snapshot_at = datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc)
        snapshot = {
            "snapshot_group_id": "snapshot-1",
            "snapshot_at": snapshot_at,
            "items": [
                {**product("A", "상품 A"), "total_quantity": Decimal("11"), "warehouses": []},
                {**product("B", "상품 B"), "total_quantity": Decimal("3"), "warehouses": []},
            ],
        }
        with patch(
            "app.services.inventory_analysis_service.get_latest_snapshot",
            return_value=snapshot,
        ) as snapshot_lookup:
            result = service.analyze("inventory_low_stock", 1, threshold="10")
            second_user_result = service.analyze("inventory_low_stock", 2, threshold="10")
        self.assertEqual([item["item_code"] for item in result["items"]], ["B"])
        self.assertEqual(result["analysis"]["data_source"], "snapshot")
        self.assertEqual(result["analysis"]["snapshot_at"], snapshot_at)
        self.assertIn("2026-07-15 15:30", result["answer"])
        self.assertEqual(fake.product_lookup_calls, 0)
        self.assertEqual(fake.location_lookup_calls, 0)
        self.assertEqual(second_user_result["items"], result["items"])
        self.assertEqual(snapshot_lookup.call_count, 2)

    def test_missing_snapshot_never_falls_back_to_external_lookup(self):
        service, fake = self.service()
        service.db = Mock()
        with patch(
            "app.services.inventory_analysis_service.get_latest_snapshot",
            return_value={"snapshot_group_id": None, "snapshot_at": None, "items": []},
        ):
            with self.assertRaises(InventorySnapshotUnavailableError):
                service.analyze("inventory_low_stock", 1, threshold="10")
        self.assertEqual(fake.product_lookup_calls, 0)
        self.assertEqual(fake.location_lookup_calls, 0)


if __name__ == "__main__":
    unittest.main()
