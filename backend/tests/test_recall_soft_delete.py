"""Soft deletion keeps recall records while removing them from work queues."""

import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_preview import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import (
    APPLICATION_RECEIVED, IN_PROGRESS, ORDER_CONFIRMED, ORDER_EXPORTED,
    REVIEW_REQUIRED, SHIPPED, RecallApplication, RecallApplicationUploadBatch,
    RecallDuplicateResolutionHistory, RecallOrderBatch, RecallStatusHistory,
)
from app.models.user import User
from app.services.recall_application_service import get_recall_summary, list_recall_applications
from app.services.recall_order_service import list_orders, order_summary, preview_orders


ROOT = "/online/recall/applications"


class RecallSoftDeleteTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__,
                      RecallOrderBatch.__table__, RecallApplication.__table__, RecallStatusHistory.__table__,
                      RecallDuplicateResolutionHistory.__table__):
            table.create(self.engine, checkfirst=True)
        self.db = Session(self.engine)
        self.db.add(User(id=1, username="operator", password_hash="test", name="담당자", role="user",
                         menu_permissions=["online_recall"]))
        self.db.add(RecallApplicationUploadBatch(id=1, source_filename="test.xlsx", source_sha256="a" * 64,
                                                 total_rows=7, valid_count=7, uploaded_by=1))
        self.db.flush()
        states = (
            (1, APPLICATION_RECEIVED, None, False),
            (2, IN_PROGRESS, None, False),
            (3, REVIEW_REQUIRED, None, True),
            (4, SHIPPED, None, False),
            (5, IN_PROGRESS, ORDER_EXPORTED, False),
            (6, IN_PROGRESS, ORDER_CONFIRMED, False),
            (7, REVIEW_REQUIRED, None, False),
        )
        for number, status, order_status, duplicate in states:
            item = RecallApplication(
                id=number, upload_batch_id=1, source_row_number=number + 1,
                application_date=date(2026, 9, 29), quantity=1,
                customer_name="고객{}".format(number), phone_original="010{:08d}".format(number),
                phone_normalized="010{:08d}".format(number), address="원효로 138",
                serial_number="SER-{}".format(number), replacement_shipping_agreement="동의",
                current_status=status, duplicate_flag=duplicate, created_by=1,
            )
            if order_status:
                item.order_status = order_status
            self.db.add(item)
        self.db.commit()
        self.user = SimpleNamespace(id=1, username="operator", name="담당자", role="user",
                                    menu_permissions=["online_recall"])
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.audit_patch = patch("app.api.routers.recall_preview.record_audit_log", return_value=True)
        self.audit = self.audit_patch.start()
        self.addCleanup(self.audit_patch.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def delete(self, client, ids, reason="업무상 오등록 확인", category="오등록"):
        return client.post(ROOT + "/bulk-delete", json={"ids": ids, "reason": reason,
                                                        "reason_category": category})

    def test_mixed_allowed_states_soft_delete_and_all_read_paths_exclude_them(self):
        self.db.get(RecallApplication, 1).duplicate_registration_count = 3
        self.db.get(RecallApplication, 2).duplicate_registration_attempt = True
        self.db.commit()
        before_registration = list_recall_applications(
            self.db, keyword=None, status="DUPLICATE_REGISTRATION", page=1, page_size=10
        )
        self.assertEqual({item.id for item in before_registration["items"]}, {1, 2})
        self.assertEqual(order_summary(self.db)["pending_count"], 1)
        with TestClient(self.app) as client:
            registration_before = client.get(ROOT, params={"status": "DUPLICATE_REGISTRATION"})
            result = self.delete(client, [1, 2, 3, 7])
            all_list = client.get(ROOT, params={"include_duplicates": "true"})
            duplicate_list = client.get(ROOT, params={"duplicate_only": "true"})
            registration_list = client.get(ROOT, params={"status": "DUPLICATE_REGISTRATION"})
            detail = client.get(ROOT + "/2")
            status_change = client.patch(ROOT + "/bulk-status", json={"ids": [2],
                "status": "SHIPPED", "reason": "처리"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(registration_before.json()["total"], 2)
        self.assertEqual(result.json()["deleted"], 4)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(RecallApplication)), 7)
        self.assertEqual([self.db.get(RecallApplication, item).is_deleted for item in (1, 2, 3, 7)],
                         [True, True, True, True])
        deleted = self.db.get(RecallApplication, 3)
        self.assertEqual((deleted.deleted_by, deleted.delete_reason), (1, "업무상 오등록 확인"))
        self.assertIsNotNone(deleted.deleted_at)
        self.assertEqual(all_list.json()["total"], 3)
        self.assertEqual(duplicate_list.json()["total"], 0)
        self.assertEqual(registration_list.json()["total"], 0)
        self.assertEqual((detail.status_code, status_change.status_code), (404, 400))
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 3, "received_count": 0, "remaining_count": 0,
            "in_progress_count": 2, "shipped_count": 1,
        })
        self.assertEqual(order_summary(self.db)["pending_count"], 0)
        self.assertEqual(list_orders(self.db, status="", page=1, page_size=30)["total"], 2)
        with self.assertRaises(ValueError):
            preview_orders(self.db, [2])
        self.audit.assert_called_once()
        audit_data = self.audit.call_args.kwargs
        self.assertEqual(audit_data["action_type"], "delete")
        self.assertEqual(audit_data["after_data"]["application_ids"], [1, 2, 3, 7])
        self.assertEqual(audit_data["after_data"]["reason_category"], "오등록")
        self.assertNotIn("원효로", str(audit_data))
        self.assertNotIn("업무상 오등록 확인", str(audit_data))

    def test_order_and_shipping_states_can_be_soft_deleted_with_history_preserved(self):
        self.db.add(RecallStatusHistory(recall_application_id=4, previous_status=IN_PROGRESS,
                                        new_status=SHIPPED, changed_by=1, change_type="BULK", reason="발송"))
        self.db.commit()
        with TestClient(self.app) as client:
            response = self.delete(client, [4, 5, 6], category="테스트 데이터")
            listed = client.get(ROOT, params={"include_duplicates": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(listed.json()["total"], 4)
        for number in (4, 5, 6):
            item = self.db.get(RecallApplication, number)
            self.assertTrue(item.is_deleted)
            self.assertEqual(item.delete_reason_category, "테스트 데이터")
        self.assertEqual(self.db.get(RecallApplication, 5).order_status, ORDER_EXPORTED)
        self.assertEqual(self.db.get(RecallApplication, 6).order_status, ORDER_CONFIRMED)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(RecallStatusHistory)
                                        .where(RecallStatusHistory.recall_application_id == 4)), 1)

    def test_permission_and_reason_validation(self):
        with TestClient(self.app) as client:
            empty_reason = self.delete(client, [1], reason=" ")
            no_selection = self.delete(client, [])
            self.user.menu_permissions = []
            forbidden = self.delete(client, [1])
        self.assertEqual((empty_reason.status_code, no_selection.status_code, forbidden.status_code),
                         (400, 400, 403))
        self.assertFalse(self.db.get(RecallApplication, 1).is_deleted)


if __name__ == "__main__":
    unittest.main()
