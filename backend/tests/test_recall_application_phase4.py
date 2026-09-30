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
    RecallDuplicateResolutionHistory,
)
from app.models.user import User
from app.models.recall_target import RecallTarget, RecallTargetUploadBatch
from app.services.recall_application_service import (
    bulk_change_recall_applications, change_recall_application_status, commit_recall_applications,
    get_recall_application_detail,
)
from app.services.recall_order_service import order_summary, preview_orders
from tests.test_recall_application_phase3 import row, workbook


class RecallApplicationPhase4Test(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__, RecallApplication.__table__, RecallTargetUploadBatch.__table__, RecallTarget.__table__, RecallStatusHistory.__table__, RecallDuplicateResolutionHistory.__table__):
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

    def bulk_change(self, client, ids, status=IN_PROGRESS, reason="일괄 상태 변경"):
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

    def test_manual_status_cannot_reverse_progress_or_shipped(self):
        with TestClient(self.app) as client:
            self.assertEqual(self.change(client, IN_PROGRESS).status_code, 200)
            reverse = self.change(client, APPLICATION_RECEIVED)
            self.assertEqual(self.bulk_change(client, [self.application_id], status=SHIPPED).status_code, 200)
            shipped_reverse = self.change(client, IN_PROGRESS)
        self.assertEqual([reverse.status_code, shipped_reverse.status_code], [400, 400])
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, SHIPPED)

    def test_shipped_recovery_records_reason_history_audit_and_summary(self):
        with TestClient(self.app) as client:
            self.assertEqual(self.change(client, IN_PROGRESS, "진행 시작").status_code, 200)
            self.assertEqual(self.bulk_change(client, [self.application_id], status=SHIPPED).status_code, 200)
            before = client.get("/online/recall/applications/summary")
            self.audit_mock.reset_mock()
            missing_reason = self.change(client, APPLICATION_RECEIVED, "  ")
            recovered = self.change(client, APPLICATION_RECEIVED, "발송 취소")
            after = client.get("/online/recall/applications/summary")
            detail = client.get(self.path())

        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(before.json(), {
            "total_count": 1, "received_count": 0, "remaining_count": 0,
            "in_progress_count": 0, "shipped_count": 1,
        })
        self.assertEqual(after.json(), {
            "total_count": 1, "received_count": 1, "remaining_count": 1,
            "in_progress_count": 0, "shipped_count": 0,
        })
        self.assertEqual(detail.json()["current_status"], APPLICATION_RECEIVED)
        history = self.histories()[-1]
        self.assertEqual((history.previous_status, history.new_status, history.change_type, history.reason, history.changed_by),
                         (SHIPPED, APPLICATION_RECEIVED, "MANUAL", "발송 취소", 1))
        self.audit_mock.assert_called_once()
        audit_kwargs = self.audit_mock.call_args.kwargs
        self.assertEqual(audit_kwargs["before_data"], {"current_status": SHIPPED})
        self.assertEqual(audit_kwargs["after_data"], {"current_status": APPLICATION_RECEIVED})
        for private_value in ("홍길동", "010-1111-2222", "발송 취소"):
            self.assertNotIn(private_value, audit_kwargs["action_summary"])

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
        self.assertEqual(summary.json()["received_count"], 0)

    def test_manual_progress_then_bulk_ship_updates_summary_api(self):
        with TestClient(self.app) as client:
            progress = self.change(client, IN_PROGRESS, "처리 시작")
            progress_summary = client.get("/online/recall/applications/summary")
            progress_list = client.get("/online/recall/applications", params={"status": IN_PROGRESS})
            shipped = self.bulk_change(client, [self.application_id], status=SHIPPED)
            shipped_summary = client.get("/online/recall/applications/summary")
        self.assertEqual((progress.status_code, shipped.status_code), (200, 200))
        self.assertEqual(progress_list.json()["total"], 1)
        self.assertEqual(progress_summary.json(), {
            "total_count": 1, "received_count": 0, "remaining_count": 0,
            "in_progress_count": 1, "shipped_count": 0,
        })
        self.assertEqual(shipped_summary.json(), {
            "total_count": 1, "received_count": 0, "remaining_count": 0,
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

    def test_bulk_next_stage_updates_each_history_summary_and_audit(self):
        second_id = self.add_application("김둘", "01022223333", "SER-002")
        with TestClient(self.app) as client:
            progress = self.bulk_change(client, [self.application_id, second_id])
            progress_summary = client.get("/online/recall/applications/summary")
            response = self.bulk_change(client, [self.application_id, second_id], status=SHIPPED)
            summary = client.get("/online/recall/applications/summary")
            listing = client.get("/online/recall/applications", params={"status": SHIPPED})
            detail = client.get(self.path())
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress_summary.json(), {
            "total_count": 2, "received_count": 0, "remaining_count": 0,
            "in_progress_count": 2, "shipped_count": 0,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual((response.json()["requested"], response.json()["updated"], response.json()["skipped"], response.json()["failed"]), (2, 2, 0, 0))
        self.assertEqual([item["result"] for item in response.json()["results"]], ["UPDATED", "UPDATED"])
        self.assertEqual((summary.json()["remaining_count"], summary.json()["received_count"], summary.json()["shipped_count"], listing.json()["total"]), (0, 0, 2, 2))
        self.assertEqual(detail.json()["status_history"][0]["new_status"], SHIPPED)
        bulk_histories = [entry for entry in self.histories() if entry.change_type == "BULK"]
        self.assertEqual(len(bulk_histories), 4)
        self.assertEqual({(entry.previous_status, entry.new_status, entry.changed_by, entry.reason) for entry in bulk_histories},
                         {(APPLICATION_RECEIVED, IN_PROGRESS, 1, "일괄 상태 변경"),
                          (IN_PROGRESS, SHIPPED, 1, "일괄 상태 변경")})
        self.assertEqual(self.audit_mock.call_count, 2)
        for audit_call in self.audit_mock.call_args_list:
            self.assertNotIn("홍길동", audit_call.kwargs["action_summary"])
            self.assertNotIn("010", audit_call.kwargs["action_summary"])

    def test_bulk_rejects_mixed_statuses_and_missing_ids_without_partial_writes(self):
        shipped_id = self.add_application("김발송", "01022223333", "SER-002")
        stopped_id = self.add_application("김중지", "01033334444", "SER-003")
        review_id = self.add_application("김확인", "01044445555", "SER-004")
        bulk_change_recall_applications(self.db, ids=[shipped_id], status=IN_PROGRESS, reason="진행", user_id=1)
        bulk_change_recall_applications(self.db, ids=[shipped_id], status=SHIPPED, reason="발송", user_id=1)
        change_recall_application_status(self.db, application_id=stopped_id, status=STOPPED, reason="중지", user_id=1)
        change_recall_application_status(self.db, application_id=review_id, status=REVIEW_REQUIRED, reason="확인", user_id=1)
        before = len(self.histories())
        with TestClient(self.app) as client:
            mixed = self.bulk_change(client, [self.application_id, shipped_id, stopped_id, review_id])
            missing = self.bulk_change(client, [self.application_id, 99999])
            direct_ship = self.bulk_change(client, [self.application_id], status=SHIPPED)
        self.assertEqual([mixed.status_code, missing.status_code, direct_ship.status_code], [400, 400, 400])
        self.assertEqual(len(self.histories()), before)
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, APPLICATION_RECEIVED)
        self.assertEqual(self.db.get(RecallApplication, stopped_id).current_status, STOPPED)
        self.assertEqual(self.db.get(RecallApplication, review_id).current_status, REVIEW_REQUIRED)

    def test_bulk_rejects_invalid_payload_without_writes(self):
        with TestClient(self.app) as client:
            invalid_status = self.bulk_change(client, [self.application_id], status=STOPPED)
            duplicate_ids = self.bulk_change(client, [self.application_id, self.application_id])
            empty_reason = self.bulk_change(client, [self.application_id], reason=" ")
        self.assertEqual([invalid_status.status_code, duplicate_ids.status_code, empty_reason.status_code], [400, 400, 400])
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, APPLICATION_RECEIVED)
        self.assertEqual(len(self.histories()), 1)
        self.audit_mock.assert_not_called()

    def test_bulk_requires_online_recall_permission(self):
        self.user.menu_permissions = ["assets"]
        with TestClient(self.app) as client:
            response = self.bulk_change(client, [self.application_id])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(len(self.histories()), 1)

    def test_bulk_commit_failure_rolls_back_all_rows_and_histories(self):
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

    def edit_values(self, **changes):
        detail = get_recall_application_detail(self.db, self.application_id)
        fields = ("application_date", "quantity", "customer_name", "phone_original", "address",
                  "memo", "serial_number", "lot_number", "pickup_agreement", "pickup_date",
                  "replacement_shipping_agreement")
        return dict({field: value.isoformat() if hasattr(value, "isoformat") else value
                     for field in fields for value in [detail[field]]}, **changes)

    def test_edit_fields_normalizes_phone_and_logs_names_only(self):
        values = self.edit_values(customer_name="수정 고객", phone_original="011 9876 5432",
                                  address="서울시 수정 주소", memo="수정 메모", pickup_agreement="미동의",
                                  replacement_shipping_agreement="동의")
        with TestClient(self.app) as client:
            response = client.patch(self.path(), json=values)
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()["application"]
        self.assertEqual((detail["customer_name"], detail["phone_original"], detail["phone_normalized"]),
                         ("수정 고객", "011 9876 5432", "01198765432"))
        self.assertEqual((detail["address"], detail["memo"], detail["pickup_agreement"]),
                         ("서울시 수정 주소", "수정 메모", "미동의"))
        self.assertEqual(len(self.histories()), 1)
        audit = self.audit_mock.call_args.kwargs
        self.assertEqual((audit["action_type"], audit["target_id"]), ("update", self.application_id))
        self.assertIn("phone_original", audit["action_summary"])
        self.assertNotIn("011 9876 5432", str(audit))
        self.assertNotIn("서울시 수정 주소", str(audit))

    def test_edit_serial_duplicate_and_resolution_history(self):
        other_id = self.add_application("다른 고객", "01022223333", "SER-OTHER")
        with TestClient(self.app) as client:
            duplicate = client.patch(self.path(), json=self.edit_values(serial_number="ser-other"))
            self.assertEqual((duplicate.status_code, duplicate.json()["application"]["duplicate_reason"]),
                             (200, "SERIAL"))
            keep = client.patch("/online/recall/applications/duplicates/{}/resolve".format(self.application_id),
                                json={"action": "KEEP", "reason": "추가 검토 필요"})
            self.assertEqual(keep.status_code, 200)
            cleared = client.patch(self.path(), json=self.edit_values(serial_number="SER-CLEARED"))
        self.assertEqual(cleared.status_code, 200, cleared.text)
        self.assertTrue(cleared.json()["application"]["duplicate_flag"])
        self.assertEqual(cleared.json()["application"]["duplicate_resolution"], "KEEP")
        self.assertEqual(len(cleared.json()["application"]["duplicate_history"]), 1)
        self.assertEqual(self.db.get(RecallApplication, other_id).serial_number, "SER-OTHER")

    def test_edit_phone_duplicate_and_clear_after_normal_resolution(self):
        self.add_application("다른 고객", "01022223333", "SER-OTHER")
        with TestClient(self.app) as client:
            duplicate = client.patch(self.path(), json=self.edit_values(phone_original="010 2222 3333"))
            self.assertEqual(duplicate.status_code, 200, duplicate.text)
            self.assertEqual(duplicate.json()["application"]["duplicate_reason"], "PHONE")
            normal = client.patch("/online/recall/applications/duplicates/{}/resolve".format(self.application_id),
                                  json={"action": "NORMAL", "reason": "별도 접수 확인"})
            self.assertEqual(normal.status_code, 200)
            unchanged_keys = client.patch(self.path(), json=self.edit_values(memo="확인된 별도 접수"))
            self.assertFalse(unchanged_keys.json()["application"]["duplicate_flag"])
            new_duplicate = client.patch(self.path(), json=self.edit_values(serial_number="SER-OTHER"))
        self.assertEqual(new_duplicate.status_code, 200, new_duplicate.text)
        self.assertTrue(new_duplicate.json()["application"]["duplicate_flag"])
        self.assertIsNone(new_duplicate.json()["application"]["duplicate_resolution"])
        self.assertEqual(len(new_duplicate.json()["application"]["duplicate_history"]), 1)

    def test_edit_unreadable_phone_requires_review_with_history(self):
        with TestClient(self.app) as client:
            response = client.patch(self.path(), json=self.edit_values(phone_original="연락처 확인"))
        self.assertEqual(response.status_code, 200, response.text)
        detail = response.json()["application"]
        self.assertEqual((detail["phone_original"], detail["phone_normalized"], detail["current_status"]),
                         ("연락처 확인", "", REVIEW_REQUIRED))
        self.assertEqual((len(self.histories()), self.histories()[-1].change_type), (2, "EDIT_VALIDATION"))
        self.assertEqual(detail["review_reason_codes"], ["PHONE_INVALID"])

    def test_review_reasons_are_coded_and_consistent_in_list_and_detail(self):
        content = workbook(row(**{"성함": "검토 고객", "*연락처": "연락처 확인",
                                  "주소지": "미정", "*시리얼번호": None}))
        commit_recall_applications(self.db, file_bytes=content, source_filename="review.xlsx",
                                   selected_row_numbers=[2], user_id=1)
        review_id = self.db.scalar(select(RecallApplication.id).where(RecallApplication.customer_name == "검토 고객"))
        expected = ["PHONE_INVALID", "SERIAL_CHECK", "ADDRESS_CHECK"]
        with TestClient(self.app) as client:
            listing = client.get("/online/recall/applications", params={"include_duplicates": "true"})
            detail = client.get("/online/recall/applications/{}".format(review_id))
        self.assertEqual((listing.status_code, detail.status_code), (200, 200))
        items = {item["id"]: item for item in listing.json()["items"]}
        self.assertEqual(items[review_id]["current_status"], REVIEW_REQUIRED)
        self.assertEqual(items[review_id]["review_reason_codes"], expected)
        self.assertEqual(detail.json()["review_reason_codes"], expected)
        self.assertEqual(items[self.application_id]["review_reason_codes"], [])
        self.assertEqual(self.db.get(RecallApplication, review_id).review_reason_codes, expected)
        self.assertNotIn("연락처 확인", str(expected))

    def test_legacy_review_reasons_derive_without_changing_status(self):
        content = workbook(row(**{"성함": "기존 고객", "*시리얼번호": None}))
        commit_recall_applications(self.db, file_bytes=content, source_filename="legacy.xlsx",
                                   selected_row_numbers=[2], user_id=1)
        legacy = self.db.scalar(select(RecallApplication).where(RecallApplication.customer_name == "기존 고객"))
        legacy.review_reason_codes = None
        self.db.commit()
        with TestClient(self.app) as client:
            detail = client.get("/online/recall/applications/{}".format(legacy.id))
        self.assertEqual(detail.json()["review_reason_codes"], ["SERIAL_CHECK"])
        self.assertEqual(legacy.current_status, REVIEW_REQUIRED)
        self.assertIsNone(legacy.review_reason_codes)

    def test_manual_review_has_classified_reason_without_raw_reason(self):
        with TestClient(self.app) as client:
            response = self.change(client, REVIEW_REQUIRED, "고객과 별도 확인")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["application"]["review_reason_codes"], ["MANUAL_REVIEW"])
        self.assertEqual(self.db.get(RecallApplication, self.application_id).review_reason_codes, ["MANUAL_REVIEW"])

    def test_review_and_normal_received_rows_advance_together_and_keep_warning(self):
        review_id = self.add_application("검토 고객", "01022223333", None)
        with TestClient(self.app) as client:
            before = client.get("/online/recall/applications/{}".format(review_id)).json()
            progress = self.bulk_change(client, [self.application_id, review_id], status=IN_PROGRESS)
            after = client.get("/online/recall/applications/{}".format(review_id)).json()
            listing = client.get("/online/recall/applications", params={"include_duplicates": "true"}).json()
        self.assertEqual(before["current_status"], REVIEW_REQUIRED)
        self.assertEqual(before["workflow_status"], APPLICATION_RECEIVED)
        self.assertEqual(before["review_reason_codes"], ["SERIAL_CHECK"])
        self.assertEqual(progress.status_code, 200, progress.text)
        self.assertEqual((after["current_status"], after["workflow_status"]), (IN_PROGRESS, IN_PROGRESS))
        self.assertEqual(after["review_reason_codes"], ["SERIAL_CHECK"])
        self.assertEqual(next(item for item in listing["items"] if item["id"] == review_id)["review_reason_codes"], ["SERIAL_CHECK"])
        self.assertEqual(after["status_history"][0]["previous_status"], REVIEW_REQUIRED)
        self.assertEqual(order_summary(self.db)["pending_count"], 2)
        self.assertEqual(preview_orders(self.db, [review_id])["item_count"], 1)

        fields = self.edit_values()
        fields = {field: after[field] for field in fields}
        fields["serial_number"] = "SER-FIXED"
        with TestClient(self.app) as client:
            fixed = client.patch("/online/recall/applications/{}".format(review_id), json=fields)
        self.assertEqual(fixed.status_code, 200, fixed.text)
        self.assertEqual(fixed.json()["application"]["current_status"], IN_PROGRESS)
        self.assertEqual(fixed.json()["application"]["review_reason_codes"], [])

    def test_progress_review_can_ship_and_duplicate_stays_out_of_scm(self):
        duplicate_id = self.add_application("중복 검토", "010-1111-2222", None)
        with TestClient(self.app) as client:
            progress = self.bulk_change(client, [duplicate_id], status=IN_PROGRESS)
            detail = client.get("/online/recall/applications/{}".format(duplicate_id)).json()
        self.assertEqual(progress.status_code, 200, progress.text)
        self.assertTrue(detail["duplicate_flag"])
        self.assertEqual(detail["review_reason_codes"], ["SERIAL_CHECK"])
        self.assertEqual(order_summary(self.db)["pending_count"], 0)
        with self.assertRaises(ValueError):
            preview_orders(self.db, [duplicate_id])
        with TestClient(self.app) as client:
            resolved = client.patch("/online/recall/applications/duplicates/{}/resolve".format(duplicate_id),
                                    json={"action": "NORMAL", "reason": "별도 접수 확인"})
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(preview_orders(self.db, [duplicate_id])["item_count"], 1)
        with TestClient(self.app) as client:
            shipped = self.bulk_change(client, [duplicate_id], status=SHIPPED)
            final = client.get("/online/recall/applications/{}".format(duplicate_id)).json()
        self.assertEqual(shipped.status_code, 200, shipped.text)
        self.assertEqual(final["current_status"], SHIPPED)
        self.assertEqual(final["review_reason_codes"], ["SERIAL_CHECK"])

    def test_review_set_during_progress_keeps_original_next_stage(self):
        with TestClient(self.app) as client:
            self.assertEqual(self.change(client, IN_PROGRESS).status_code, 200)
            self.assertEqual(self.change(client, REVIEW_REQUIRED).status_code, 200)
            detail = client.get(self.path()).json()
            shipped = self.bulk_change(client, [self.application_id], status=SHIPPED)
        self.assertEqual(detail["workflow_status"], IN_PROGRESS)
        self.assertEqual(detail["review_reason_codes"], ["MANUAL_REVIEW"])
        self.assertEqual(shipped.status_code, 200, shipped.text)
        self.assertEqual(self.db.get(RecallApplication, self.application_id).current_status, SHIPPED)

    def test_single_review_detail_can_advance_without_clearing_reason(self):
        review_id = self.add_application("상세 검토", "01022223333", None)
        with TestClient(self.app) as client:
            response = client.patch("/online/recall/applications/{}/status".format(review_id),
                                    json={"status": IN_PROGRESS, "reason": "업무 진행"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["application"]["current_status"], IN_PROGRESS)
        self.assertEqual(response.json()["application"]["review_reason_codes"], ["SERIAL_CHECK"])
        history = self.db.scalar(select(RecallStatusHistory).where(
            RecallStatusHistory.recall_application_id == review_id,
            RecallStatusHistory.new_status == IN_PROGRESS,
        ))
        self.assertEqual((history.previous_status, history.change_type), (REVIEW_REQUIRED, "MANUAL"))

    def test_edit_invalid_values_and_protected_fields(self):
        with TestClient(self.app) as client:
            invalid = client.patch(self.path(), json=self.edit_values(quantity="1.5", pickup_date="2026-02-30"))
            protected = client.patch(self.path(), json=dict(self.edit_values(), current_status=SHIPPED))
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(set(invalid.json()["detail"]["fields"]), {"quantity", "pickup_date"})
        self.assertEqual(protected.status_code, 422)
        self.assertEqual(len(self.histories()), 1)
        self.audit_mock.assert_not_called()

    def test_edit_requires_permission(self):
        self.user.menu_permissions = ["assets"]
        with TestClient(self.app) as client:
            response = client.patch(self.path(), json=self.edit_values(customer_name="차단"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.db.get(RecallApplication, self.application_id).customer_name, "홍길동")


if __name__ == "__main__":
    unittest.main()
