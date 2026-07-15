import logging
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.core.auth import get_current_user
from app.main import app
from app.models.user import User
from app.services.ai_assistant_service import AiAssistantService
from app.services.ai_intent_service import analyze_intent, normalize_message


class AiIntentServiceTest(unittest.TestCase):
    def test_empty_question(self):
        with self.assertRaisesRegex(ValueError, "질문을 입력해주세요"):
            normalize_message("   ")

    def test_question_over_500_characters(self):
        with self.assertRaisesRegex(ValueError, "500자 이하"):
            normalize_message("가" * 501)

    def test_normalization(self):
        self.assertEqual(normalize_message("  ABC   재고!!  "), "abc 재고")

    def test_greeting(self):
        self.assertEqual(analyze_intent("안녕하세요").intent, "greeting")

    def test_help(self):
        self.assertEqual(analyze_intent("뭐 할 수 있어?").intent, "help")

    def test_inventory_search_and_keyword(self):
        result = analyze_intent("벤틀리 재고 알려줘")
        self.assertEqual(result.intent, "inventory_search")
        self.assertEqual(result.entities["keyword"], "벤틀리")

    def test_low_stock_default_threshold(self):
        result = analyze_intent("부족 재고 보여줘")
        self.assertEqual(result.intent, "inventory_low_stock")
        self.assertEqual(result.entities["threshold"], 10)

    def test_low_stock_number_and_comparison(self):
        result = analyze_intent("재고 5개 미만 품목 보여줘")
        self.assertEqual(result.intent, "inventory_low_stock")
        self.assertEqual(result.entities, {"threshold": 5, "comparison": "미만"})

    def test_item_code_extraction(self):
        result = analyze_intent("품목코드 ABC-123 재고 알려줘")
        self.assertEqual(result.intent, "inventory_item_code")
        self.assertEqual(result.entities["item_code"], "ABC-123")

    def test_asset_search(self):
        self.assertEqual(analyze_intent("홍길동 노트북 자산 알려줘").intent, "asset_search")

    def test_vehicle_search(self):
        self.assertEqual(analyze_intent("37마0788 차량 정보 알려줘").intent, "vehicle_search")

    def test_vehicle_expiration_and_period(self):
        result = analyze_intent("이번 달 보험 만료 차량 알려줘")
        self.assertEqual(result.intent, "vehicle_expiration")
        self.assertEqual(result.entities["period"], "this_month")

    def test_inspection_schedule(self):
        result = analyze_intent("7일 이내 점검 일정 알려줘")
        self.assertEqual(result.intent, "inspection_schedule")
        self.assertEqual(result.entities["period"], "within_7_days")

    def test_unknown(self):
        self.assertEqual(analyze_intent("오늘 점심 메뉴 추천").intent, "unknown")

    def test_priority_prefers_low_stock_over_inventory(self):
        self.assertEqual(analyze_intent("재고 10개 이하 품목").intent, "inventory_low_stock")

    def test_priority_prefers_item_code(self):
        self.assertEqual(analyze_intent("품목코드 ABC123 부족 재고").intent, "inventory_item_code")

    def test_inventory_alert_intents_remain_rule_based(self):
        cases = {
            "오늘 확인해야 할 재고 있어?": "inventory_alert_summary",
            "품절 품목 보여줘": "inventory_out_of_stock",
            "재고 부족 품목 알려줘": "inventory_alert_low_stock",
            "음수 재고 있어?": "inventory_alert_negative",
            "급격히 줄어든 품목 보여줘": "inventory_rapid_decrease",
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                self.assertEqual(analyze_intent(question).intent, expected)


class AiAssistantServiceTest(unittest.TestCase):
    def test_inventory_returns_pending_message(self):
        inventory = Mock()
        inventory.recommend_products.return_value = {
            "mode": "recommendation", "query": "벤틀리", "total": 1,
            "items": [{"item_code": "B001", "item_name": "벤틀리", "unit": "EA"}],
            "has_more": False, "limit": 8,
        }
        response = AiAssistantService(inventory).process_message("벤틀리 재고 알려줘")
        self.assertTrue(response["success"])
        self.assertIn("이카운트 재고 API 연결 후", response["message"])

    def test_item_code_prompt_when_code_is_missing(self):
        response = AiAssistantService().process_message("품목코드로 재고 조회")
        self.assertIn("품목코드를 함께", response["message"])

    def test_mutating_request_is_blocked(self):
        response = AiAssistantService().process_message("차량 삭제해줘")
        self.assertEqual(response["message"], "현재 AI 업무 도우미는 조회 기능만 지원합니다.")

    def test_no_external_ai_client_is_called(self):
        with patch("httpx.Client", side_effect=AssertionError("external call")):
            response = AiAssistantService().process_message("도움말")
        self.assertEqual(response["intent"], "help")

    def test_original_question_is_not_logged(self):
        secret_question = "민감한질문원문-987654 재고 알려줘"
        inventory = Mock()
        inventory.recommend_products.return_value = {
            "mode": "recommendation", "query": "민감한질문원문-987654", "total": 0,
            "items": [], "has_more": False, "limit": 8,
        }
        with self.assertLogs("app.services.ai_assistant_service", logging.INFO) as captured:
            AiAssistantService(inventory).process_message(secret_question)
        self.assertNotIn(secret_question, " ".join(captured.output))

    def test_exact_bare_product_name_becomes_inventory_search(self):
        inventory = Mock()
        inventory.recommend_products.return_value = {
            "mode": "recommendation", "query": "토스터블랙", "total": 1,
            "items": [{"item_code": "T001", "item_name": "토스터블랙", "unit": "EA"}],
            "has_more": False, "limit": 8,
        }
        viewer = User(id=3, username="viewer", name="조회자", password_hash="-", role="user", menu_permissions=["dashboard"])
        response = AiAssistantService(inventory).process_message("토스터블랙", viewer.id, viewer)
        self.assertEqual(response["intent"], "inventory_search")
        self.assertEqual(response["data"]["item_code"], "T001")
        inventory.recommend_products.assert_called_once_with("토스터블랙", limit=8)

    def test_multiple_products_return_recommendations_without_inventory_lookup(self):
        inventory = Mock()
        inventory.recommend_products.return_value = {
            "mode": "recommendation", "query": "토스터", "total": 2,
            "items": [
                {"item_code": "T001", "item_name": "토스터블랙", "unit": "EA"},
                {"item_code": "T002", "item_name": "토스터화이트", "unit": "EA"},
            ],
            "has_more": False, "limit": 8,
        }
        viewer = User(id=3, username="viewer", name="조회자", password_hash="-", role="user", menu_permissions=["dashboard"])
        response = AiAssistantService(inventory).process_message("토스터", viewer.id, viewer)
        self.assertEqual(response["intent"], "inventory_recommendation")
        self.assertEqual(len(response["data"]["items"]), 2)
        inventory.get_inventory_by_location.assert_not_called()

    def test_no_product_keeps_bare_general_fallback(self):
        inventory = Mock()
        inventory.recommend_products.return_value = {
            "mode": "recommendation", "query": "없는품목", "total": 0,
            "items": [], "has_more": False, "limit": 8,
        }
        viewer = User(id=3, username="viewer", name="조회자", password_hash="-", role="user", menu_permissions=["dashboard"])
        response = AiAssistantService(inventory).process_message("없는품목", viewer.id, viewer)
        self.assertEqual(response["intent"], "unknown")

    def test_general_sentence_is_not_treated_as_product_name(self):
        inventory = Mock()
        viewer = User(id=3, username="viewer", name="조회자", password_hash="-", role="user", menu_permissions=["dashboard"])
        response = AiAssistantService(inventory).process_message("오늘 점심 메뉴 추천", viewer.id, viewer)
        self.assertEqual(response["intent"], "unknown")
        inventory.search_products.assert_not_called()


class AiAssistantRouteTest(unittest.TestCase):
    def tearDown(self):
        app.dependency_overrides.clear()

    def test_authenticated_user_can_chat(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=3, username="viewer", name="조회자", password_hash="-", role="user",
        )
        response = TestClient(app).post("/ai/chat", json={"message": "안녕하세요"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["intent"], "greeting")

    def test_unauthenticated_user_gets_401(self):
        response = TestClient(app).post("/ai/chat", json={"message": "안녕하세요"})
        self.assertEqual(response.status_code, 401)

    def test_empty_question_returns_400(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=3, username="viewer", name="조회자", password_hash="-", role="user",
        )
        response = TestClient(app).post("/ai/chat", json={"message": "  "})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "질문을 입력해주세요.")

    def test_openapi_contains_ai_chat(self):
        self.assertIn("post", app.openapi()["paths"]["/ai/chat"])


if __name__ == "__main__":
    unittest.main()
