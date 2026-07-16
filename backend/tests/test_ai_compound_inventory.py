import unittest
from unittest.mock import Mock

from app.services.ai_assistant_service import AiAssistantService
from app.services.ai_intent_service import analyze_intent
from app.services.ai_inventory_query_service import match_warehouses


WAREHOUSES = [
    {"warehouse_code": "P1", "warehouse_name": "파주창고", "quantity": "92.5"},
    {"warehouse_code": "P2", "warehouse_name": "파주RMA", "quantity": "13"},
    {"warehouse_code": "H1", "warehouse_name": "본사", "quantity": "267"},
    {"warehouse_code": "R1", "warehouse_name": "본사RMA", "quantity": "-2.25"},
]


def inventory_response():
    return {
        "success": True, "authenticated": True, "total": 1,
        "items": [{
            "item_code": "101006", "item_name": "랜턴블랙", "size": "Black", "unit": "EA",
            "total_quantity": "370.25", "warehouses": WAREHOUSES,
        }],
        "message": "ok", "response_time_ms": 1,
    }


def exact_inventory_service():
    service = Mock()
    service.recommend_products.return_value = {
        "mode": "recommendation", "query": "랜턴블랙", "total": 1,
        "items": [{"item_code": "101006", "item_name": "랜턴블랙", "unit": "EA"}],
        "has_more": False, "limit": 8, "match_type": "exact_name",
    }
    service.get_aggregated_inventory.return_value = inventory_response()
    return service


class AiCompoundInventoryTest(unittest.TestCase):
    def test_supported_sentence_shapes_are_parsed(self):
        cases = {
            "랜턴블랙 파주 재고 알려줘": ("랜턴블랙", None, "파주"),
            "랜턴블랙 파주창고에 몇 개 있어?": ("랜턴블랙", None, "파주"),
            "품목코드 101006의 RMA 재고 보여줘": (None, "101006", "rma"),
            "뉴토스터블랙 본사만 보여줘": ("뉴토스터블랙", None, "본사"),
            "발뮤다AS창고 뉴토스터블랙 재고 알려줘": ("뉴토스터블랙", None, "발뮤다as"),
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                result = analyze_intent(question)
                self.assertEqual(result.intent, "inventory_item_warehouse_search")
                self.assertEqual((result.entities.get("keyword"), result.entities.get("item_code"), result.entities["warehouse_keyword"]), expected)

    def test_item_name_and_partial_warehouse_use_one_inventory_call(self):
        service = exact_inventory_service()
        response = AiAssistantService(service).process_message("랜턴블랙 파주 재고 알려줘")
        self.assertEqual(response["intent"], "inventory_item_warehouse_search")
        self.assertEqual(response["data"]["type"], "inventory_warehouse_result")
        self.assertEqual(response["data"]["warehouse_match_count"], 2)
        self.assertEqual(str(response["data"]["filtered_quantity"]), "105.5")
        self.assertEqual(len(response["context"]["inventory_result"]["warehouses"]), 4)
        service.get_aggregated_inventory.assert_called_once()

    def test_exact_warehouse_name_wins_over_partial(self):
        exact, match_type = match_warehouses(WAREHOUSES, "파주창고")
        self.assertEqual(match_type, "exact")
        self.assertEqual([row["warehouse_name"] for row in exact], ["파주창고"])
        partial, match_type = match_warehouses(WAREHOUSES, "파주")
        self.assertEqual(match_type, "partial")
        self.assertEqual(len(partial), 2)

    def test_item_code_and_warehouse(self):
        service = exact_inventory_service()
        service.recommend_products.return_value = {
            "mode": "recommendation", "query": "101006", "total": 1,
            "items": [{"item_code": "101006", "item_name": "랜턴블랙", "unit": "EA"}],
            "has_more": False, "limit": 8, "match_type": "exact_code",
        }
        response = AiAssistantService(service).process_message("품목코드 101006의 RMA 재고 보여줘")
        self.assertEqual(response["data"]["warehouse_match_count"], 2)
        self.assertEqual(str(response["data"]["filtered_quantity"]), "10.75")

    def test_no_warehouse_match_keeps_full_context(self):
        service = exact_inventory_service()
        response = AiAssistantService(service).process_message("랜턴블랙 부산창고 재고 알려줘")
        self.assertEqual(response["data"]["warehouse_match_count"], 0)
        self.assertIn("찾지 못했습니다", response["message"])
        self.assertEqual(len(response["context"]["inventory_result"]["warehouses"]), 4)

    def test_multiple_and_fuzzy_candidates_keep_pending_warehouse_without_inventory_call(self):
        for match_type in ("prefix", "fuzzy"):
            service = Mock()
            service.recommend_products.return_value = {
                "mode": "recommendation", "query": "랜턴", "total": 2,
                "items": [
                    {"item_code": "1", "item_name": "랜턴블랙", "match_type": match_type},
                    {"item_code": "2", "item_name": "뉴랜턴블랙", "match_type": match_type},
                ],
                "has_more": False, "limit": 8, "match_type": match_type,
            }
            question = "랜턴블렉 파주 재고 알려줘" if match_type == "fuzzy" else "랜턴 파주 재고 알려줘"
            response = AiAssistantService(service).process_message(question)
            self.assertEqual(response["data"]["type"], "product_candidates")
            self.assertEqual(response["context"]["pending_warehouse_keyword"], "파주")
            service.get_aggregated_inventory.assert_not_called()

    def test_refresh_with_warehouse_filters_after_single_requery(self):
        service = exact_inventory_service()
        context = {
            "selected_item_code": "101006", "selected_item_name": "랜턴블랙", "unit": "EA", "size": "Black",
            "last_intent": "inventory_search", "searched_at": None, "last_warehouse_filter": None,
            "last_warehouse_keyword": None, "pending_warehouse_keyword": None,
            "search_keyword": None, "product_candidates": [],
            "inventory_result": {"total_quantity": "370.25", "warehouses": WAREHOUSES},
        }
        response = AiAssistantService(service).process_message("최신 재고로 파주만 보여줘", context=context)
        self.assertEqual(response["intent"], "inventory_refresh")
        self.assertEqual(response["data"]["warehouse_match_count"], 2)
        service.get_aggregated_inventory.assert_called_once_with("101006", product=None)


if __name__ == "__main__":
    unittest.main()
