"""Phase 4 detail and manual status changes against the existing recall tables."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_preview import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import (
    APPLICATION_RECEIVED, IN_PROGRESS, REVIEW_REQUIRED, STOPPED, SHIPPED,
    RecallApplication, RecallApplicationUploadBatch, RecallStatusHistory,
)
from app.models.user import User
from app.services.recall_application_service import (
    bulk_ship_recall_applications, change_recall_application_status, commit_recall_applications,
)
from tests.test_recall_application_phase3 import row, workbook


class RecallApplicationPhase4Test(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__, RecallApplication.__table__, RecallStatusHistory.__table__):
            table.create(self.engine, checkfirst=True)
        self.db = Session(self.engine)
        self.db.add(User(id=1, username="operator", password_hash="test", name="담당자", role="user", menu_permissions=["online_recall"]))
        self.db.commit()
        commit_recall_applications(
            self.db, file_bytes=workbook(row()), source_filename="applications.xlsx",
            selected_row_numbers=[2], user_id=1,
        )
        self.application_id = self.db.scalar(select(RecallApplication.id))
        self.app = FastAPI()
        self.app.include_router(router)
        self.user = SimpleNamespace(id=1, username="operator", name="담당자", role="user", menu_permissions=["online_recall"])
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.audit = patch("app.api.routers.recall_preview.record_audit_log", return_value=True)
        self.audit_mock = self.audit.start()
        self.addCleanup(self.audit.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def path(self):
        return "/online/recall/applications/{}".format(self.application_id)

    def change(self, client, status, reason="수동 확인"):
        return client.patch(self.path() + "/status", json={"status": status, "reason": reason})

    def histories(self):
        return list(self.db.scalars(select(RecallStatusHistory).order_by(RecallStatusHistory.id)).all())

    def add_application(self, name, phone, serial):
        content = workbook(row(**{"성함": name, "*연락처": phone, "*시리얼번호": serial}))
        commit_recall_applications(
            self.db, file_bytes=content, source_filename="{}.xlsx".format(name),
            selected_row_numbers=[2], user_id=1,
        )
        return self.db.scalar(select(RecallApplication.id).where(RecallApplication.customer_name == name))

    def bulk_change(self, client, ids, status=SHIPPED, reason="일괄 발송 완료 처리"):
        return client.patch("/online/recall/applications/bulk-status", json={"ids": ids, "status": status, "reason": reason})

    def test_detail_contains_application_batch_and_latest_history(self):
        with TestClient(self.app) as client:
            response = client.get(self.path())
        self.assertEqual(response.status_code, 200)
        detail = response.json()
        self.assertEqual(detail["customer_name"], "홍길동")
        self.assertEqual(detail["phone_original"], "010-1111-2222")
        self.assertEqual(detail["upload_batch"]["source_filename"], "applications.xlsx")
        self.assertEqual(detail["created_by_name"], "담당자")
        self.assertEqual(detail["status_history"][0]["previous_status"], None)

    def test_missing_detail_and_status_change_return_404(self):
        with TestClient(self.app) as client:
            detail = client.get("/online/recall/applications/99999")
            change = client.patch("/online/recall/applications/99999/status", json={"status": STOPPED, "reason": "확인"})
        self.assertEqual((detail.status_code, change.status_code), (404, 404))

    def test_without_menu_permission_detail_and_change_are_blocked(self):
        self.user.menu_permissions = ["assets"]
        with TestClient(self.app) as client:
            detail = client.get(self.path())
            change = self.change(client, STOPPED)
        self.assertEqual((detail.status_code, change.status_code), (403, 403))
        self.assertEqual(len(self.histories()), 1)

    def test_hidden_menu_blocks_detail_and_change(self):
        self.db.add(MenuVisibilitySetting(menu_key="online_recall", visible=False))
        self.db.commit()
        with TestClient(self.app) as client:
            detail = client.get(self.path())
            change = self.change(client, STOPPED)
        self.assertEqual((detail.status_code, change.status_code), (403, 403))

    def test_received_to_stopped_records_history_actor_reason_and_audit(self):
        with TestClient(self.app) as client:
            response = self.change(client, STOPPED, "고객 요청으로 중지")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["changed"])
        self.assertEqual(response.json()["application"]["current_status"], STOPPED)
        self.assertEqual(response.json()["application"]["status_history"][0]["new_status"], STOPPED)
        history = self.histories()[-1]
        self.assertEqual((history.previous_status, history.new_status, history.changed_by, history.change_type, history.reason),
                         (APPLICATION_RECEIVED, STOPPED, 1, "MANUAL", "고객 요청으로 중지"))
        self.audit_mock.assert_called_once()
        audit_kwargs = self.audit_mock.call_args.kwargs
        self.assertEqual(audit_kwargs["menu_key"], "online_recall")
        self.assertNotIn("고객 요청으로 중지", audit_kwargs["action_summary"])

    def test_received_to_review_and_stopped_to_received(self):
        with TestClient(self.app) as client:
            review = self.change(client, REVIEW_REQUIRED)
            stopped = self.change(client, STOPPED)
            received = self.change(client, APPLICATION_RECEIVED)
        self.assertEqual([review.status_code, stopped.status_code, received.status_code], [200, 200, 200])
        self.assertEqual([item.new_status for item in self.histories()],
                         [APPLICATION_RECEIVED, REVIEW_REQUIRED, STOPPED, APPLICATION_RECEIVED])

    def test_same_status_does_not_add_history_or_audit(self):
        with TestClient(self.app) as client:
            response = self.change(client, APPLICATION_RECEIVED)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["changed"])
        self.assertEqual(len(self.histories()), 1)
        self.audit_mock.assert_not_called()

    def test_invalid_status_and_empty_reason_are_rejected(self):
        with TestClient(self.app) as client:
            forbidden = self.change(client, "SHIPPED")
            empty_reason = self.change(client, STOPPED, "  ")
        self.assertEqual((forbidden.status_code, empty_reason.status_code), (400, 400))
        self.assertEqual(len(self.histories()), 1)

    def test_failed_status_commit_rolls_back_application_and_history(self):
        with patch.object(self.db, "commit", side_effect=OperationalError("commit", {}, Exception("failure"))):
            with TestClient(self.app) as client:
                response = self.change(client, STOPPED)
        self.assertEqual(response.status_code, 500)
        self.db.expire_all()
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, APPLICATION_RECEIVED)
        self.assertEqual(len(self.histories()), 1)
        self.audit_mock.assert_not_called()

    def test_listing_filter_and_received_summary_reflect_change(self):
        with TestClient(self.app) as client:
            self.assertEqual(self.change(client, REVIEW_REQUIRED).status_code, 200)
            filtered = client.get("/online/recall/applications", params={"status": REVIEW_REQUIRED})
            received = client.get("/online/recall/applications", params={"status": APPLICATION_RECEIVED})
            summary = client.get("/online/recall/applications/summary")
        self.assertEqual(filtered.json()["total"], 1)
        self.assertEqual(filtered.json()["items"][0]["current_status"], REVIEW_REQUIRED)
        self.assertEqual(received.json()["total"], 0)
        self.assertEqual(summary.json()["remaining_count"], 0)
        self.assertEqual(summary.json()["received_count"], 1)

    def test_manual_progress_then_bulk_ship_updates_summary_api(self):
        with TestClient(self.app) as client:
            progress = self.change(client, IN_PROGRESS, "처리 시작")
            progress_summary = client.get("/online/recall/applications/summary")
            progress_list = client.get("/online/recall/applications", params={"status": IN_PROGRESS})
            shipped = self.bulk_change(client, [self.application_id])
            shipped_summary = client.get("/online/recall/applications/summary")
        self.assertEqual((progress.status_code, shipped.status_code), (200, 200))
        self.assertEqual(progress_list.json()["total"], 1)
        self.assertEqual(progress_summary.json(), {
            "total_count": 1, "received_count": 1, "remaining_count": 0,
            "in_progress_count": 1, "shipped_count": 0,
        })
        self.assertEqual(shipped_summary.json(), {
            "total_count": 1, "received_count": 1, "remaining_count": 0,
            "in_progress_count": 0, "shipped_count": 1,
        })
        self.assertEqual(self.histories()[-1].previous_status, IN_PROGRESS)

    def test_listing_returns_existing_excel_columns(self):
        with TestClient(self.app) as client:
            response = client.get("/online/recall/applications", params={"keyword": "홍길동", "status": APPLICATION_RECEIVED})
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(
            [item[key] for key in (
                "application_date", "quantity", "customer_name", "phone_original", "address", "memo",
                "serial_number", "lot_number", "pickup_agreement", "pickup_date",
                "replacement_shipping_agreement", "current_status",
            )],
            ["2026-09-22", 1, "홍길동", "010-1111-2222", "서울시 마포구 월드컵로 10", "방문 전 연락",
             "SER-001", "LOT-A", "동의", None, "동의", APPLICATION_RECEIVED],
        )

    def test_phase3_registration_still_has_initial_history(self):
        self.assertEqual(self.db.scalar(select(func.count()).select_from(RecallApplication)), 1)
        self.assertEqual(self.histories()[0].change_type, "EXCEL_REGISTRATION")

    def test_bulk_ship_updates_each_history_summary_and_audit(self):
        second_id = self.add_application("김둘", "01022223333", "SER-002")
        with TestClient(self.app) as client:
            response = self.bulk_change(client, [self.application_id, second_id])
            summary = client.get("/online/recall/applications/summary")
            listing = client.get("/online/recall/applications", params={"status": SHIPPED})
            detail = client.get(self.path())
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["requested"], response.json()["updated"], response.json()["skipped"], response.json()["failed"]), (2, 2, 0, 0))
        self.assertEqual([item["result"] for item in response.json()["results"]], ["UPDATED", "UPDATED"])
        self.assertEqual((summary.json()["remaining_count"], summary.json()["received_count"], summary.json()["shipped_count"], listing.json()["total"]), (0, 2, 2, 2))
        self.assertEqual(detail.json()["status_history"][0]["new_status"], SHIPPED)
        bulk_histories = [entry for entry in self.histories() if entry.change_type == "BULK"]
        self.assertEqual(len(bulk_histories), 2)
        self.assertEqual({(entry.previous_status, entry.new_status, entry.changed_by, entry.reason) for entry in bulk_histories},
                         {(APPLICATION_RECEIVED, SHIPPED, 1, "일괄 발송 완료 처리")})
        self.audit_mock.assert_called_once()
        self.assertNotIn("홍길동", self.audit_mock.call_args.kwargs["action_summary"])
        self.assertNotIn("010", self.audit_mock.call_args.kwargs["action_summary"])

    def test_bulk_ship_skips_shipped_and_rejects_other_states_or_missing_ids(self):
        shipped_id = self.add_application("김발송", "01022223333", "SER-002")
        stopped_id = self.add_application("김중지", "01033334444", "SER-003")
        review_id = self.add_application("김확인", "01044445555", "SER-004")
        bulk_ship_recall_applications(self.db, ids=[shipped_id], status=SHIPPED, reason="선처리", user_id=1)
        change_recall_application_status(self.db, application_id=stopped_id, status=STOPPED, reason="중지", user_id=1)
        change_recall_application_status(self.db, application_id=review_id, status=REVIEW_REQUIRED, reason="확인", user_id=1)
        before = len(self.histories())
        with TestClient(self.app) as client:
            response = self.bulk_change(client, [self.application_id, shipped_id, stopped_id, review_id, 99999])
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["requested"], response.json()["updated"], response.json()["skipped"], response.json()["failed"]), (5, 1, 1, 3))
        self.assertEqual([item["reason_code"] for item in response.json()["results"]],
                         [None, "ALREADY_SHIPPED", "INVALID_CURRENT_STATUS", "INVALID_CURRENT_STATUS", "NOT_FOUND"])
        self.assertEqual(len(self.histories()), before + 1)
        self.assertEqual(self.db.get(RecallApplication, stopped_id).current_status, STOPPED)
        self.assertEqual(self.db.get(RecallApplication, review_id).current_status, REVIEW_REQUIRED)

    def test_bulk_ship_rejects_invalid_payload_without_writes(self):
        with TestClient(self.app) as client:
            invalid_status = self.bulk_change(client, [self.application_id], status=STOPPED)
            duplicate_ids = self.bulk_change(client, [self.application_id, self.application_id])
            empty_reason = self.bulk_change(client, [self.application_id], reason=" ")
        self.assertEqual([invalid_status.status_code, duplicate_ids.status_code, empty_reason.status_code], [400, 400, 400])
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, APPLICATION_RECEIVED)
        self.assertEqual(len(self.histories()), 1)
        self.audit_mock.assert_not_called()

    def test_bulk_ship_requires_online_recall_permission(self):
        self.user.menu_permissions = ["assets"]
        with TestClient(self.app) as client:
            response = self.bulk_change(client, [self.application_id])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(self.histories()), 1)

    def test_bulk_ship_commit_failure_rolls_back_all_rows_and_histories(self):
        second_id = self.add_application("김둘", "01022223333", "SER-002")
        with patch.object(self.db, "commit", side_effect=OperationalError("commit", {}, Exception("failure"))):
            with TestClient(self.app) as client:
                response = self.bulk_change(client, [self.application_id, second_id])
        self.assertEqual(response.status_code, 500)
        self.db.expire_all()
        self.assertEqual([self.db.get(RecallApplication, item_id).current_status for item_id in (self.application_id, second_id)],
                         [APPLICATION_RECEIVED, APPLICATION_RECEIVED])
        self.assertEqual(len(self.histories()), 2)
        self.audit_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
