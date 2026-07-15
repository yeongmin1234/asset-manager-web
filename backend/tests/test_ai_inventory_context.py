import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.models.user import User
from app.services.ai_assistant_service import AiAssistantService
from app.services.ai_inventory_context_service import (
    clear_inventory_contexts,
    expire_inventory_context_for_test,
    get_inventory_context,
    save_inventory_context,
)


def inventory_item(code="00016", name="뉴토스터블랙", total="2", warehouses=None):
    return {
        "item_code": code,
        "item_name": name,
        "size": None,
        "unit": "EA",
        "total_quantity": total,
        "warehouses": warehouses if warehouses is not None else [
            {"warehouse_code": "001", "warehouse_name": "과주RMA", "quantity": "1"},
            {"warehouse_code": "002", "warehouse_name": "발뮤다AS창고", "quantity": "1"},
        ],
    }


class AiInventoryContextTest(unittest.TestCase):
    def setUp(self):
        clear_inventory_contexts()

    def tearDown(self):
        clear_inventory_contexts()
        app.dependency_overrides.clear()

    def save(self, user_id=1, items=None):
        return save_inventory_context(
            user_id=user_id,
            intent="inventory_search",
            query="뉴토스터블랙 재고 알려줘",
            items=items or [inventory_item()],
            searched_at="2026-07-15T10:00:00+09:00",
        )

    def test_context_is_separated_by_user(self):
        self.save(1, [inventory_item("A", "사용자1")])
        self.save(2, [inventory_item("B", "사용자2")])
        self.assertEqual(get_inventory_context(1).last_item_code, "A")
        self.assertEqual(get_inventory_context(2).last_item_code, "B")

    def test_single_inventory_result_is_saved(self):
        context = self.save()
        self.assertEqual(context.last_item_code, "00016")
        self.assertEqual(context.last_item_name, "뉴토스터블랙")
        self.assertEqual(len(context.last_inventory_items), 1)

    def test_warehouse_followup_uses_saved_result(self):
        self.save()
        response = AiAssistantService().process_message("어느 창고에 있어?", user_id=1)
        self.assertEqual(response["intent"], "inventory_context_warehouses")
        self.assertIn("과주RMA 1개", response["message"])
        self.assertIn("발뮤다AS창고 1개", response["message"])

    def test_total_followup_uses_saved_result(self):
        self.save()
        response = AiAssistantService().process_message("총 몇 개야?", user_id=1)
        self.assertEqual(response["message"], "현재 총재고는 2개입니다.")

    def test_followup_without_context_does_not_guess(self):
        response = AiAssistantService().process_message("아까 몇 개라고 했지?", user_id=1)
        self.assertIn("최근 조회한 재고 정보가 없습니다", response["message"])

    def test_context_expires_after_ttl(self):
        self.save()
        expire_inventory_context_for_test(1)
        self.assertIsNone(get_inventory_context(1))

    def test_non_inventory_error_does_not_clear_context(self):
        self.save()
        AiAssistantService().process_message("지원하지 않는 일반 질문", user_id=1)
        self.assertEqual(get_inventory_context(1).last_item_code, "00016")

    def test_failed_new_inventory_flow_does_not_clear_previous_context(self):
        self.save()
        # A new inventory intent alone does not overwrite context; only the authenticated
        # success callback endpoint writes a replacement result.
        AiAssistantService().process_message("없는품목 재고 알려줘", user_id=1)
        self.assertEqual(get_inventory_context(1).last_item_code, "00016")

    def test_followup_does_not_call_external_api(self):
        self.save()
        with patch("httpx.Client", side_effect=AssertionError("API must not be called")):
            response = AiAssistantService().process_message("전체 재고는?", user_id=1)
        self.assertEqual(response["intent"], "inventory_context_total")

    def test_refresh_request_returns_requery_intent(self):
        self.save()
        response = AiAssistantService().process_message("최신 재고 확인해줘", user_id=1)
        self.assertEqual(response["intent"], "inventory_refresh")
        self.assertEqual(response["data"]["item_code"], "00016")

    def test_other_user_cannot_access_context(self):
        self.save(user_id=1)
        response = AiAssistantService().process_message("어느 창고에 있어?", user_id=2)
        self.assertIn("최근 조회한 재고 정보가 없습니다", response["message"])

    def test_multiple_result_selection_and_lowest(self):
        self.save(items=[
            inventory_item("A", "첫 품목", "8", []),
            inventory_item("B", "둘째 품목", "3", []),
        ])
        second = AiAssistantService().process_message("두 번째 품목은?", user_id=1)
        self.assertIn("둘째 품목", second["message"])
        lowest = AiAssistantService().process_message("가장 재고가 적은 품목은?", user_id=1)
        self.assertIn("둘째 품목", lowest["message"])

    def test_existing_general_ai_question_is_unchanged(self):
        response = AiAssistantService().process_message("안녕하세요", user_id=1)
        self.assertEqual(response["intent"], "greeting")

    def test_authenticated_context_save_endpoint(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=7, username="user7", name="사용자", password_hash="-", role="user",
        )
        response = TestClient(app).post("/ai/inventory-context", json={
            "intent": "inventory_search",
            "query": "뉴토스터블랙 재고",
            "items": [inventory_item()],
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_inventory_context(7).last_item_code, "00016")


if __name__ == "__main__":
    unittest.main()
