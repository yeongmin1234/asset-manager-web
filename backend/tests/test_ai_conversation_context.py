import unittest
from unittest.mock import Mock

from app.services.ai_assistant_service import AiAssistantService


def context():
    return {
        "selected_item_code": "101006", "selected_item_name": "랜턴블랙",
        "unit": "EA", "size": "Black", "last_intent": "inventory_search",
        "searched_at": "2026-07-16T10:00:00+09:00", "last_warehouse_filter": None,
        "search_keyword": None, "product_candidates": [],
        "inventory_result": {"total_quantity": "372", "warehouses": [
            {"warehouse_code": "P1", "warehouse_name": "파주창고", "quantity": "92"},
            {"warehouse_code": "P2", "warehouse_name": "파주RMA", "quantity": "13"},
            {"warehouse_code": "H1", "warehouse_name": "본사", "quantity": "267"},
        ]},
    }


class AiConversationContextTest(unittest.TestCase):
    def test_followup_without_context_is_safe(self):
        response = AiAssistantService().process_message("파주만 보여줘", user_id=1, context=None)
        self.assertIn("먼저", response["message"])

    def test_partial_warehouse_filter_reuses_context(self):
        inventory = Mock()
        response = AiAssistantService(inventory).process_message("파주만 보여줘", context=context())
        self.assertEqual(response["intent"], "inventory_warehouse_filter")
        self.assertIn("총 105개", response["message"])
        self.assertEqual(len(response["data"]["inventory_response"]["items"][0]["warehouses"]), 2)
        inventory.get_aggregated_inventory.assert_not_called()

    def test_no_matching_warehouse(self):
        response = AiAssistantService().process_message("부산만 보여줘", context=context())
        self.assertIn("찾지 못했습니다", response["message"])

    def test_all_and_other_warehouses(self):
        filtered = AiAssistantService().process_message("파주만 보여줘", context=context())
        other = AiAssistantService().process_message("다른 창고는?", context=filtered["context"])
        self.assertEqual(other["data"]["inventory_response"]["items"][0]["warehouses"][0]["warehouse_name"], "본사")
        all_result = AiAssistantService().process_message("전체 창고 보여줘", context=filtered["context"])
        self.assertEqual(len(all_result["data"]["inventory_response"]["items"][0]["warehouses"]), 3)

    def test_scalar_followups_do_not_call_inventory_api(self):
        inventory = Mock()
        cases = {
            "총 몇 개야?": "372개", "품목코드는?": "101006",
            "이름은?": "랜턴블랙", "단위는?": "EA", "규격은?": "Black",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertIn(expected, AiAssistantService(inventory).process_message(question, context=context())["message"])
        inventory.get_aggregated_inventory.assert_not_called()

    def test_refresh_is_the_only_followup_that_queries_inventory(self):
        inventory = Mock()
        inventory.get_aggregated_inventory.return_value = {
            "success": True, "authenticated": True, "total": 1,
            "items": [{"item_code": "101006", "item_name": "랜턴블랙", "size": "Black", "unit": "EA", "total_quantity": "373", "warehouses": []}],
            "message": "ok", "response_time_ms": 1,
        }
        response = AiAssistantService(inventory).process_message("최신 재고로 확인해줘", context=context())
        self.assertEqual(response["intent"], "inventory_refresh")
        inventory.get_aggregated_inventory.assert_called_once_with("101006", product=None)

    def test_context_clear(self):
        response = AiAssistantService().process_message("대화 초기화", context=context())
        self.assertEqual(response["intent"], "context_clear")
        self.assertIsNone(response.get("context"))

    def test_oversized_context_is_rejected(self):
        bad = context()
        bad["selected_item_name"] = "x" * 40000
        with self.assertRaises(ValueError):
            AiAssistantService().process_message("총 몇 개야?", context=bad)


if __name__ == "__main__":
    unittest.main()
