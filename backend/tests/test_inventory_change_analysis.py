from datetime import datetime, timezone
from decimal import Decimal
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.db.database import get_db
from app.main import app
from app.models.inventory_schedule import InventorySchedule
from app.models.inventory_snapshot import InventorySnapshot
from app.models.user import User
from app.schemas.inventory_snapshot import InventoryChangeResponse
from app.services.ai_assistant_service import AiAssistantService
from app.services.ai_intent_service import analyze_intent
from app.services.inventory_change_analysis_service import InventoryChangeAnalysisService


class InventoryChangeAnalysisTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
        )
        InventorySchedule.__table__.create(self.engine)
        InventorySnapshot.__table__.create(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.Session()
        self.schedule = InventorySchedule(
            name="재고", run_time=datetime.strptime("08:00", "%H:%M").time(),
            timezone="Asia/Seoul", is_active=True, target_mode="all_supported_items",
            target_item_codes=[],
        )
        self.db.add(self.schedule)
        self.db.commit()
        self.now = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        self.service = InventoryChangeAnalysisService(now_func=lambda: self.now)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def add_group(self, group_id, snapshot_at, quantities, names=None, schedule_id=None):
        names = names or {}
        for code, quantity in quantities.items():
            value = Decimal(str(quantity))
            self.db.add(InventorySnapshot(
                snapshot_group_id=group_id,
                schedule_id=schedule_id if schedule_id is not None else self.schedule.id,
                snapshot_at=snapshot_at,
                row_type="total",
                item_code=code,
                item_name=names.get(code, "품목 {}".format(code)),
                unit="EA",
                warehouse_code="",
                quantity=value,
                total_quantity=value,
            ))
        self.db.commit()

    def add_today_pair(self):
        self.add_group("morning", datetime(2026, 7, 14, 23, 0, tzinfo=timezone.utc), {
            "A": "10.0000000000", "B": "0", "C": "-1", "OLD": "5", "U": "2",
        }, {"A": "사과", "B": "바나나"})
        self.add_group("afternoon", datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc), {
            "A": "5", "B": "4", "C": "-3", "NEW": "7", "U": "2",
        }, {"A": "사과", "B": "바나나"})

    def test_morning_afternoon_change_decimal_rate_and_statuses(self):
        self.add_today_pair()
        result = self.service.compare(self.db, mode="today_morning_afternoon")
        InventoryChangeResponse(**result)
        items = {item["item_code"]: item for item in result["items"]}
        self.assertTrue(result["available"])
        self.assertEqual(items["A"]["change_quantity"], Decimal("-5.0000000000"))
        self.assertEqual(items["A"]["change_rate"], Decimal("-50.00"))
        self.assertEqual(items["B"]["status"], "newly_added")
        self.assertEqual(items["B"]["change_rate_label"], "신규 증가")
        self.assertEqual(items["C"]["after_quantity"], Decimal("-3.0000000000"))
        self.assertEqual(items["OLD"]["status"], "no_longer_present")
        self.assertEqual(items["NEW"]["status"], "newly_added")
        self.assertEqual(items["U"]["status"], "unchanged")

    def test_increased_decreased_unchanged_and_extremes(self):
        self.add_today_pair()
        increased = self.service.compare(self.db, mode="today_morning_afternoon", direction="increased")
        decreased = self.service.compare(self.db, mode="today_morning_afternoon", direction="decreased")
        unchanged = self.service.compare(self.db, mode="today_morning_afternoon", direction="unchanged")
        self.assertEqual([item["item_code"] for item in increased["items"]], ["NEW", "B"])
        self.assertEqual({item["item_code"] for item in decreased["items"]}, {"A", "C", "OLD"})
        self.assertEqual([item["item_code"] for item in unchanged["items"]], ["U"])
        self.assertEqual(increased["largest_increase"]["change_quantity"], Decimal("7.0000000000"))
        self.assertEqual(decreased["largest_decrease"]["change_quantity"], Decimal("-5.0000000000"))
        largest = self.service.compare(
            self.db, mode="today_morning_afternoon", direction="decreased",
            extreme="largest_decrease",
        )
        self.assertEqual({item["change_quantity"] for item in largest["items"]}, {Decimal("-5.0000000000")})
        self.assertIn("가장 많이 감소", largest["answer"])

    def test_negative_transition_from_zero(self):
        self.add_group("before", datetime(2026, 7, 14, 23, 0, tzinfo=timezone.utc), {"A": "0"})
        self.add_group("after", datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc), {"A": "-2"})
        item = self.service.compare(self.db, mode="today_morning_afternoon")["items"][0]
        self.assertEqual(item["status"], "negative_transition")
        self.assertIsNone(item["change_rate"])
        self.assertEqual(item["change_rate_label"], "음수 전환")

    def test_today_vs_yesterday_same_time_and_keyword_code_filters(self):
        self.add_group("yesterday", datetime(2026, 7, 14, 6, 25, tzinfo=timezone.utc), {"A": "9", "B": "3"}, {"A": "사과"})
        self.add_group("today", datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc), {"A": "4", "B": "3"}, {"A": "사과"})
        by_code = self.service.compare(self.db, mode="today_vs_yesterday", item_code="a")
        by_name = self.service.compare(self.db, mode="today_vs_yesterday", keyword="사과")
        self.assertEqual(by_code["items"][0]["item_code"], "A")
        self.assertEqual(by_name["items"][0]["change_quantity"], Decimal("-5.0000000000"))
        self.assertIn("어제 동일 시간대", by_code["selection_note"])

    def test_custom_time_uses_nearest_real_snapshots(self):
        self.add_group("one", datetime(2026, 7, 14, 23, 5, tzinfo=timezone.utc), {"A": "1"})
        self.add_group("two", datetime(2026, 7, 15, 6, 35, tzinfo=timezone.utc), {"A": "2"})
        result = self.service.compare(
            self.db,
            start_at=datetime(2026, 7, 15, 8, 0),
            end_at=datetime(2026, 7, 15, 15, 30),
            mode="custom",
        )
        self.assertEqual((result["start_snapshot_group_id"], result["end_snapshot_group_id"]), ("one", "two"))
        self.assertIn("가장 가까운 실제", result["selection_note"])

    def test_specific_schedule_a_vs_b_uses_each_latest_snapshot(self):
        afternoon_schedule = InventorySchedule(
            name="오후 재고", run_time=datetime.strptime("15:30", "%H:%M").time(),
            timezone="Asia/Seoul", is_active=True, target_mode="all_supported_items",
            target_item_codes=[],
        )
        self.db.add(afternoon_schedule)
        self.db.commit()
        self.add_group(
            "schedule-a", datetime(2026, 7, 14, 23, 0, tzinfo=timezone.utc),
            {"A": "10"}, schedule_id=self.schedule.id,
        )
        self.add_group(
            "schedule-b", datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc),
            {"A": "7"}, schedule_id=afternoon_schedule.id,
        )
        result = self.service.compare(
            self.db, start_schedule_id=self.schedule.id,
            end_schedule_id=afternoon_schedule.id,
        )
        self.assertEqual((result["start_snapshot_group_id"], result["end_snapshot_group_id"]), ("schedule-a", "schedule-b"))
        self.assertEqual(result["items"][0]["change_quantity"], Decimal("-3.0000000000"))

    def test_missing_comparable_snapshots(self):
        self.add_group("only", datetime(2026, 7, 15, 6, 30, tzinfo=timezone.utc), {"A": "1"})
        result = self.service.compare(self.db)
        self.assertFalse(result["available"])
        self.assertEqual(result["items"], [])
        self.assertIn("비교할 재고 이력이 없습니다", result["answer"])


class InventoryChangeIntentTest(unittest.TestCase):
    def test_change_intents_and_entities(self):
        cases = {
            "오늘 오전보다 재고가 줄어든 품목 보여줘": ("inventory_decreased", "today_morning_afternoon", "decreased"),
            "오늘 가장 많이 증가한 품목은?": ("inventory_largest_increase", "latest_previous", "increased"),
            "오늘 재고 변화 요약해줘": ("inventory_change_summary", "latest_previous", "all"),
            "최근 재고 변화가 큰 품목 보여줘": ("inventory_history_compare", "latest_previous", "all"),
            "어제보다 재고가 줄어든 품목 알려줘": ("inventory_decreased", "today_vs_yesterday", "decreased"),
        }
        for question, expected in cases.items():
            with self.subTest(question=question):
                result = analyze_intent(question)
                self.assertEqual((result.intent, result.entities["mode"], result.entities["direction"]), expected)
                if "품목 보여줘" in question:
                    self.assertNotIn("keyword", result.entities)

        named = analyze_intent("뉴토스터블랙 오전 오후 재고 비교해줘")
        self.assertEqual(named.entities["keyword"], "뉴토스터블랙")

    def test_item_code_history_compare(self):
        result = analyze_intent("품목코드 101011 오전 8시와 오후 3시 30분 재고 비교해줘")
        self.assertEqual(result.intent, "inventory_change_compare")
        self.assertEqual(result.entities["item_code"], "101011")
        response = AiAssistantService().process_message("품목코드 101011 오전 8시와 오후 3시 30분 재고 비교해줘")
        self.assertEqual(response["intent"], "inventory_change_compare")


class InventoryChangeRouteTest(unittest.TestCase):
    def test_openapi_and_existing_realtime_path(self):
        paths = app.openapi()["paths"]
        self.assertIn("get", paths["/inventory/analysis/compare"])
        self.assertIn("get", paths["/inventory/analysis/summary"])
        self.assertIn("get", paths["/inventory/search"])

    def test_unauthenticated_is_401_and_no_dashboard_permission_is_403(self):
        self.assertEqual(TestClient(app).get("/inventory/analysis/compare").status_code, 401)
        app.dependency_overrides[get_current_user] = lambda: User(
            id=2, username="user", name="일반", password_hash="-", role="user",
            menu_permissions=[],
        )
        try:
            response = TestClient(app).get("/inventory/analysis/compare")
        finally:
            app.dependency_overrides.clear()
        self.assertEqual(response.status_code, 403)

    def test_admin_and_dashboard_user_are_allowed(self):
        safe_result = InventoryChangeAnalysisService._empty_response("테스트")
        for user in (
            User(id=1, username="admin", name="관리자", password_hash="-", role="admin", menu_permissions=[]),
            User(id=2, username="user", name="사용자", password_hash="-", role="user", menu_permissions=["dashboard"]),
        ):
            with self.subTest(role=user.role):
                app.dependency_overrides[get_current_user] = lambda user=user: user
                app.dependency_overrides[get_db] = lambda: object()
                try:
                    with patch("app.api.routers.inventory.InventoryChangeAnalysisService") as service:
                        service.return_value.compare.return_value = safe_result
                        response = TestClient(app).get("/inventory/analysis/compare")
                finally:
                    app.dependency_overrides.clear()
                self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
