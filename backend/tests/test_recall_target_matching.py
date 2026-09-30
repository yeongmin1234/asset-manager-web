"""Phase 7 conservative matching and target statistics."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_preview import router as application_router
from app.api.routers.recall_targets import router as target_router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import APPLICATION_RECEIVED, IN_PROGRESS, SHIPPED, RecallApplication, RecallApplicationUploadBatch, RecallStatusHistory
from app.models.recall_target import RecallTarget, RecallTargetUploadBatch
from app.models.user import User
from app.services.recall_target_matching import channel_summary, manual_match, matching_summary, run_auto_matching, unmatch
from tests.test_recall_application_phase3 import row as application_row, workbook as application_workbook
from tests.test_recall_targets import target as target_row, workbook as target_workbook


ROOT = "/online/recall/targets"


class RecallTargetMatchingTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__,
                      RecallApplication.__table__, RecallTargetUploadBatch.__table__, RecallTarget.__table__, RecallStatusHistory.__table__):
            table.create(self.engine)
        self.db = Session(self.engine)
        self.db.add(User(id=1, username="operator", password_hash="test", name="담당자", role="user", menu_permissions=["online_recall"]))
        self.db.add(RecallApplicationUploadBatch(id=1, source_filename="applications.xlsx", source_sha256="a" * 64,
                                                 total_rows=0, valid_count=0, uploaded_by=1))
        self.db.add(RecallTargetUploadBatch(id=1, original_filename="targets.xlsx", total_count=0, normal_count=0,
                                            duplicate_count=0, review_count=0, excluded_count=0, created_by=1))
        self.db.commit()
        self.user = SimpleNamespace(id=1, role="user", menu_permissions=["online_recall"])
        self.app = FastAPI()
        self.app.include_router(target_router)
        self.app.include_router(application_router)
        self.app.dependency_overrides[get_current_user] = lambda: self.user
        self.app.dependency_overrides[get_db] = lambda: self.db
        target_audit = patch("app.api.routers.recall_targets.record_audit_log", return_value=True)
        application_audit = patch("app.api.routers.recall_preview.record_audit_log", return_value=True)
        self.audit = target_audit.start()
        self.app_audit = application_audit.start()
        self.addCleanup(target_audit.stop)
        self.addCleanup(application_audit.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def application(self, serial, phone, status=APPLICATION_RECEIVED, duplicate=False):
        application = RecallApplication(upload_batch_id=1, source_row_number=self.db.query(RecallApplication).count() + 2,
                                        customer_name="신청자", phone_original=phone, phone_normalized="".join(ch for ch in phone if ch.isdigit()),
                                        address="서울시 마포구 10", serial_number=serial, current_status=status,
                                        duplicate_flag=duplicate, created_by=1)
        self.db.add(application)
        self.db.flush()
        return application

    def target(self, serial, phone, channel="온라인몰", duplicate=False):
        target = RecallTarget(batch_id=1, source_row_number=self.db.query(RecallTarget).count() + 2,
                              sales_channel=channel, customer_name="대상자", phone_raw=phone,
                              phone_normalized="".join(ch for ch in phone if ch.isdigit()), address="서울시 마포구 10",
                              serial_number=serial, duplicate_flag=duplicate, created_by=1)
        self.db.add(target)
        self.db.flush()
        return target

    def test_serial_phone_priority_conflict_and_multiple_candidates(self):
        one = self.application("S-1", "010-1111-1111")
        two = self.application("S-2", "010-2222-2222")
        serial = self.target("S-1", "010-9999-9999")
        phone = self.target("missing", "010-2222-2222")
        conflict = self.target("S-1", "010-2222-2222")
        self.application("S-3", "010-3333-3333")
        self.application("S-3", "010-4444-4444")
        multiple_serial = self.target("S-3", "010-8888-8888")
        self.application("S-5", "010-5555-5555")
        self.application("S-6", "010-5555-5555")
        multiple_phone = self.target(None, "010-5555-5555")
        self.db.commit()
        result = run_auto_matching(self.db, user_id=1)
        self.db.commit()
        self.assertEqual(result, {"matched": 2, "review": 3, "unmatched": 0})
        self.assertEqual((serial.match_status, serial.match_method, serial.matched_application_id), ("MATCHED", "SERIAL", one.id))
        self.assertEqual((phone.match_status, phone.match_method, phone.matched_application_id), ("MATCHED", "PHONE", two.id))
        self.assertEqual(conflict.match_review_reason, "SERIAL_PHONE_CONFLICT")
        self.assertEqual(multiple_serial.match_review_reason, "MULTIPLE_SERIAL_MATCH")
        self.assertEqual(multiple_phone.match_review_reason, "MULTIPLE_PHONE_MATCH")

    def test_existing_link_duplicate_guards_and_rerun_preserves_match(self):
        application = self.application("S-1", "010-1111-1111")
        first = self.target("S-1", "010-1111-1111")
        second = self.target("S-1", "010-1111-1111")
        duplicate_target = self.target("S-1", "010-1111-1111", duplicate=True)
        duplicate_application = self.application("S-2", "010-2222-2222", duplicate=True)
        unsafe = self.target("S-2", "010-2222-2222")
        unmatched = self.target("S-9", "010-9999-9999")
        self.db.commit()
        run_auto_matching(self.db, user_id=1)
        self.db.commit()
        self.assertEqual(first.matched_application_id, application.id)
        self.assertEqual(second.match_review_reason, "APPLICATION_ALREADY_MATCHED")
        self.assertEqual(duplicate_target.match_review_reason, "RAW_TARGET_DUPLICATE")
        self.assertEqual(unsafe.match_review_reason, "DUPLICATE_APPLICATION")
        self.assertEqual(unmatched.match_status, "UNMATCHED")
        self.application("S-9", "010-9999-9999")
        self.db.commit()
        run_auto_matching(self.db, user_id=1)
        self.db.commit()
        self.assertEqual(first.matched_application_id, application.id)
        self.assertEqual(unmatched.match_status, "MATCHED")

    def test_order_number_alone_does_not_match_without_application_field(self):
        self.application(None, "010-1111-1111")
        target = self.target(None, "010-9999-9999")
        target.original_order_no = "ORDER-1"
        self.db.commit()
        result = run_auto_matching(self.db, user_id=1)
        self.db.commit()
        self.assertEqual(result["unmatched"], 1)
        self.assertEqual(target.match_status, "UNMATCHED")

    def test_manual_match_release_summary_channels_filters_and_permission(self):
        self.assertEqual(channel_summary(self.db), [])
        progress = self.application("S-1", "010-1111-1111", status=IN_PROGRESS)
        shipped = self.application("S-2", "010-2222-2222", status=SHIPPED)
        first = self.target("S-1", "010-1111-1111", channel="몰A")
        second = self.target("S-2", "010-2222-2222", channel="몰A")
        third = self.target("S-3", "010-3333-3333", channel="몰B")
        self.db.commit()
        run_auto_matching(self.db, user_id=1)
        self.db.commit()
        self.assertEqual(matching_summary(self.db), {"total_count": 3, "received_count": 2,
                                                      "remaining_count": 1, "in_progress_count": 1, "shipped_count": 1})
        self.assertEqual(channel_summary(self.db)[0]["application_rate"], 100.0)
        with TestClient(self.app) as client:
            listing = client.get(ROOT, params={"match_status": "MATCHED", "page_size": 10})
            summary = client.get(ROOT + "/matching/summary")
            channels = client.get(ROOT + "/matching/channels")
            detail = client.get(ROOT + "/{}".format(first.id))
            conflict = client.post(ROOT + "/{}/match".format(third.id), json={"application_id": progress.id})
            release = client.post(ROOT + "/{}/unmatch".format(second.id))
            manual = client.post(ROOT + "/{}/match".format(third.id), json={"application_id": shipped.id})
            rerun = client.post(ROOT + "/matching/run")
            self.user.menu_permissions = []
            forbidden = client.post(ROOT + "/matching/run")
        self.assertEqual((listing.status_code, listing.json()["total"]), (200, 2))
        self.assertEqual(summary.json()["remaining_count"], 1)
        self.assertEqual(channels.json()[0]["matched_count"], 2)
        self.assertEqual(detail.json()["application"]["current_status"], IN_PROGRESS)
        self.assertEqual((conflict.status_code, release.status_code, manual.status_code, rerun.status_code, forbidden.status_code),
                         (409, 200, 200, 200, 403))
        self.assertEqual(third.match_method, "MANUAL")
        self.assertEqual(release.json()["match_status"], "UNMATCHED")
        self.assertEqual(second.match_review_reason, "APPLICATION_ALREADY_MATCHED")
        self.assertTrue(any(call.kwargs.get("action_type") == "auto_match" for call in self.audit.call_args_list))
        self.assertNotIn("010-1111-1111", str(self.audit.call_args_list))

    def test_target_and_application_commits_trigger_matching(self):
        self.application("S-1", "010-1111-1111")
        self.db.commit()
        target_bytes = target_workbook(target_row(serial="S-1", phone="010-1111-1111"))
        with TestClient(self.app) as client:
            raw = client.post(ROOT + "/commit", files={"file": ("targets.xlsx", target_bytes)})
        self.assertEqual(raw.status_code, 200, raw.text)
        self.assertEqual(raw.json()["matching"]["matched"], 1)
        pending = self.target("S-2", "010-2222-2222")
        self.db.commit()
        app_bytes = application_workbook(application_row(**{"*시리얼번호": "S-2", "*연락처": "010-2222-2222"}))
        with TestClient(self.app) as client:
            application = client.post("/online/recall/applications/commit", files={"file": ("applications.xlsx", app_bytes)},
                                      data={"selected_row_numbers": "[2]"})
        self.assertEqual(application.status_code, 200, application.text)
        self.assertEqual(application.json()["matching"]["matched"], 1)
        self.assertEqual(pending.match_status, "MATCHED")


if __name__ == "__main__":
    unittest.main()
