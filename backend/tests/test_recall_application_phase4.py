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
    APPLICATION_RECEIVED, REVIEW_REQUIRED, STOPPED,
    RecallApplication, RecallApplicationUploadBatch, RecallStatusHistory,
)
from app.models.user import User
from app.services.recall_application_service import commit_recall_applications
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
        self.assertEqual(summary.json()["received"], 0)

    def test_phase3_registration_still_has_initial_history(self):
        self.assertEqual(self.db.scalar(select(func.count()).select_from(RecallApplication)), 1)
        self.assertEqual(self.histories()[0].change_type, "EXCEL_REGISTRATION")


if __name__ == "__main__":
    unittest.main()
