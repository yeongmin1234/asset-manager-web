"""Raw target preview, cumulative import and read APIs."""

import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_targets import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import RecallApplication, RecallApplicationUploadBatch
from app.models.recall_target import RecallTarget, RecallTargetUploadBatch
from app.models.user import User


ROOT = "/online/recall/targets"
HEADERS = ["판매 채널", "주문번호", "고객명", "연락처", "주소", "배송메시지", "시리얼번호", "LOT 번호", "구매일"]


def workbook(*rows):
    book = Workbook()
    sheet = book.active
    sheet.append(HEADERS)
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def target(name="고객", phone="010-1234-5678", order="O-1", serial="S-1", address="서울시 마포구 10", purchase="2026-09-30"):
    return ["온라인몰", order, name, phone, address, "문 앞", serial, "LOT-1", purchase]


class RecallTargetsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__, RecallApplication.__table__, RecallTargetUploadBatch.__table__, RecallTarget.__table__):
            table.create(self.engine)
        self.db = Session(self.engine)
        self.db.add(User(id=1, username="operator", password_hash="test", name="담당자", role="user", menu_permissions=["online_recall"]))
        self.db.commit()
        self.user = SimpleNamespace(id=1, role="user", menu_permissions=["online_recall"])
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        audit_patch = patch("app.api.routers.recall_targets.record_audit_log", return_value=True)
        self.audit = audit_patch.start()
        self.addCleanup(audit_patch.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def post(self, client, action, data):
        return client.post(ROOT + action, files={"file": ("targets.xlsx", data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})

    def test_preview_commit_duplicate_review_excluded_and_accumulation(self):
        first = workbook(target())
        second = workbook(
            target(name="시리얼 중복", phone="010-2222-3333", order="O-2"),
            target(name="전화 중복", serial="S-3", order="O-3"),
            target(name="주문 중복", phone="010-4444-5555", serial="S-4"),
            target(name="파일 내부", phone="010-6666-7777", serial="S-5", order="O-5"),
            target(name="파일 내부 반복", phone="010-8888-9999", serial="S-5", order="O-6"),
            target(name="확인 필요", phone="abc", serial="S-7", order="O-7"),
            [None] * 9,
        )
        with TestClient(self.app) as client:
            initial = self.post(client, "/commit", first)
            preview = self.post(client, "/preview", second)
            self.assertEqual(self.db.query(RecallTarget).count(), 1)
            commit = self.post(client, "/commit", second)
            listing = client.get(ROOT, params={"status": "duplicate", "page_size": 10})
            summary = client.get(ROOT + "/summary")
            batches = client.get(ROOT + "/batches")
        self.assertEqual(initial.status_code, 200, initial.text)
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()["summary"], {"total_rows": 7, "valid": 1, "duplicate": 4, "review": 1, "excluded": 1})
        self.assertEqual([row["duplicate_reason"] for row in preview.json()["rows"][:5]], ["SERIAL", "PHONE", "ORDER_NO", None, "SERIAL"])
        self.assertEqual(commit.status_code, 200, commit.text)
        self.assertEqual(commit.json()["registered"], 6)
        self.assertEqual(self.db.query(RecallTarget).count(), 7)
        self.assertEqual(listing.json()["total"], 4)
        self.assertEqual(summary.json(), {"total_count": 7, "normal_count": 2, "duplicate_count": 4, "review_count": 1})
        self.assertEqual(len(batches.json()), 2)
        items = self.db.scalars(select(RecallTarget).order_by(RecallTarget.id)).all()
        self.assertEqual(items[0].phone_raw, "010-1234-5678")
        self.assertEqual(items[0].phone_normalized, "01012345678")
        self.assertEqual(items[1].duplicate_reference_id, items[0].id)
        self.assertEqual(items[5].duplicate_reference_id, items[4].id)
        self.assertTrue(items[6].review_required)
        self.assertEqual(items[6].review_reason, "PHONE_INVALID")
        self.assertNotIn("010-1234-5678", str(self.audit.call_args.kwargs))

    def test_search_filters_page_sizes_and_permission(self):
        rows = [target(name="고객{}".format(i), phone="010-{:04d}-{:04d}".format(i, i), order="O-{}".format(i), serial="S-{}".format(i)) for i in range(25)]
        with TestClient(self.app) as client:
            self.assertEqual(self.post(client, "/commit", workbook(*rows)).status_code, 200)
            for size in (10, 20, 50, 100):
                data = client.get(ROOT, params={"page_size": size}).json()
                self.assertEqual((data["total"], len(data["items"])), (25, min(25, size)))
            self.assertEqual(client.get(ROOT, params={"keyword": "S-24"}).json()["total"], 1)
            self.assertEqual(client.get(ROOT, params={"keyword": "01000000000"}).json()["total"], 1)
            self.assertEqual(client.get(ROOT, params={"status": "valid"}).json()["total"], 25)
            self.user.menu_permissions = []
            self.assertEqual(client.get(ROOT).status_code, 403)
            self.assertEqual(self.post(client, "/preview", workbook(target())).status_code, 403)

    def test_review_reasons_for_serial_date_and_address(self):
        data = workbook(
            target(name="날짜 확인", serial="", purchase="2026-19-80"),
            target(name="주소 확인", serial="S-2", order="O-2", phone="010-9999-9999", address="미정"),
        )
        with TestClient(self.app) as client:
            preview = self.post(client, "/preview", data)
        self.assertEqual(preview.status_code, 200)
        self.assertIn("SERIAL_CHECK", preview.json()["rows"][0]["reasons"])
        self.assertIn("DATE_INVALID", preview.json()["rows"][0]["reasons"])
        self.assertIn("ADDRESS_CHECK", preview.json()["rows"][1]["reasons"])

    def test_bulk_delete_unmatched_and_review_updates_live_counts_but_keeps_batch(self):
        data = workbook(target(), target(name="확인 필요", phone="abc", order="O-2", serial="S-2"))
        with TestClient(self.app) as client:
            self.assertEqual(self.post(client, "/commit", data).status_code, 200)
            review_target = self.db.scalar(select(RecallTarget).where(RecallTarget.review_required.is_(True)))
            review_target.match_status = "REVIEW"
            self.db.commit()
            items = client.get(ROOT).json()["items"]
            self.assertEqual({item["match_status"] for item in items}, {"UNMATCHED", "REVIEW"})
            ids = [item["id"] for item in items]
            batches_before = client.get(ROOT + "/batches").json()
            self.audit.reset_mock()
            deleted = client.post(ROOT + "/bulk-delete", json={"ids": ids, "reason": "오등록"})
            self.assertEqual(deleted.status_code, 200, deleted.text)
            self.assertEqual(deleted.json()["deleted"], 2)
            self.assertEqual(client.get(ROOT).json()["total"], 0)
            self.assertEqual(client.get(ROOT, params={"keyword": "S-1"}).json()["total"], 0)
            self.assertEqual(client.get(ROOT + "/summary").json()["total_count"], 0)
            self.assertEqual(client.get(ROOT + "/matching/summary").json()["total_count"], 0)
            self.assertEqual(client.get(ROOT + "/matching/channels").json(), [])
            self.assertEqual(client.get(ROOT + "/batches").json(), batches_before)
            self.assertEqual(client.post(ROOT + "/matching/run").json()["unmatched"], 0)
            self.assertEqual(client.post(ROOT + "/bulk-delete", json={"ids": ids, "reason": "재삭제"}).status_code, 409)
        targets = self.db.scalars(select(RecallTarget).order_by(RecallTarget.id)).all()
        self.assertEqual(len(targets), 2)
        self.assertTrue(all(item.is_deleted and item.deleted_at and item.deleted_by == 1 and item.delete_reason == "오등록" for item in targets))
        logs = [call.kwargs for call in self.audit.call_args_list if call.kwargs.get("action_type") == "delete"]
        self.assertEqual({log["target_id"] for log in logs}, set(ids))
        self.assertTrue(all(log["after_data"]["delete_reason"] == "오등록" for log in logs))
        self.assertTrue(all("customer_name" not in str(log) and "phone_raw" not in str(log) for log in logs))

    def test_bulk_delete_rejects_matched_selection_atomically_and_checks_permission(self):
        with TestClient(self.app) as client:
            self.assertEqual(self.post(client, "/commit", workbook(target(), target(name="두번째", phone="abc", order="O-2", serial="S-2"))).status_code, 200)
            items = self.db.scalars(select(RecallTarget).order_by(RecallTarget.id)).all()
            items[0].match_status = "MATCHED"
            self.db.commit()
            ids = [item.id for item in items]
            blocked = client.post(ROOT + "/bulk-delete", json={"ids": ids, "reason": "오등록"})
            self.assertEqual(blocked.status_code, 409)
            self.assertIn("매칭을 해제", blocked.json()["detail"])
            self.assertEqual(client.get(ROOT).json()["total"], 2)
            self.assertEqual(client.post(ROOT + "/bulk-delete", json={"ids": [ids[1]], "reason": " "}).status_code, 409)
            self.user.menu_permissions = []
            self.assertEqual(client.post(ROOT + "/bulk-delete", json={"ids": [ids[1]], "reason": "오등록"}).status_code, 403)
        self.assertFalse(any(item.is_deleted for item in items))


if __name__ == "__main__":
    unittest.main()
