import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_preview import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.recall_application import (
    APPLICATION_RECEIVED,
    IN_PROGRESS,
    ORDER_CONFIRMED,
    ORDER_EXPORTED,
    REVIEW_REQUIRED,
    STOPPED,
    SHIPPED,
    RecallApplication,
    RecallApplicationUploadBatch,
    RecallStatusHistory,
    RecallDuplicateResolutionHistory,
    RecallOrderBatch,
)
from app.models.user import User
from app.models.recall_target import RecallTarget, RecallTargetUploadBatch
from app.services.recall_application_excel import EXCEL_COLUMNS
from app.services.recall_application_service import (
    bulk_change_recall_applications,
    bulk_soft_delete_recall_applications,
    change_recall_application_status,
    commit_recall_applications,
    create_recall_application_manually,
    get_recall_application_detail,
    get_recall_summary,
    list_recall_applications,
)
from app.services.recall_order_service import export_orders, order_summary, preview_orders


HEADERS = list(EXCEL_COLUMNS)


def row(**changes):
    values = {
        "신청일자": "2026.09.22", "수량": 1, "성함": "홍길동",
        "*연락처": "010-1111-2222", "주소지": "서울시 마포구 월드컵로 10",
        "메모": "방문 전 연락", "*시리얼번호": "SER-001", "LOT 번호": "LOT-A",
        "기존 필터 회수 동의": "동의", "회수 일자": None,
        "대체 필터 출고 동의": "동의",
    }
    values.update(changes)
    return [values[header] for header in HEADERS]


def workbook(*rows):
    book = Workbook()
    sheet = book.active
    sheet.title = "자산업로드양식"
    sheet.append(HEADERS)
    for values in rows:
        sheet.append(values)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


class RecallApplicationPhase3Test(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        for table in (User.__table__, MenuVisibilitySetting.__table__, RecallApplicationUploadBatch.__table__, RecallOrderBatch.__table__, RecallApplication.__table__, RecallTargetUploadBatch.__table__, RecallTarget.__table__, RecallStatusHistory.__table__, RecallDuplicateResolutionHistory.__table__):
            table.create(self.engine, checkfirst=True)
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def commit(self, content, selected=(2,), filename="applications.xlsx"):
        return commit_recall_applications(
            self.db, file_bytes=content, source_filename=filename,
            selected_row_numbers=list(selected), user_id=1,
        )

    def count(self, model):
        return int(self.db.scalar(select(func.count()).select_from(model)) or 0)

    def manual_values(self, **changes):
        values = dict(zip(EXCEL_COLUMNS.values(), row()))
        values.update(changes)
        return values

    def test_manual_registration_reuses_excel_validation_and_matching(self):
        first = create_recall_application_manually(
            self.db, values=self.manual_values(phone_original="010-1111-2222"), user_id=1)
        application = self.db.get(RecallApplication, first["id"])
        self.assertEqual(application.phone_normalized, "01011112222")
        self.assertEqual(application.current_status, APPLICATION_RECEIVED)
        self.assertEqual(application.duplicate_flag, False)
        history = self.db.scalar(select(RecallStatusHistory).where(
            RecallStatusHistory.recall_application_id == application.id))
        self.assertEqual(history.change_type, "MANUAL_REGISTRATION")
        second = create_recall_application_manually(
            self.db, values=self.manual_values(serial_number="SER-002", memo="별도 신청"), user_id=1)
        self.assertTrue(self.db.get(RecallApplication, second["id"]).duplicate_flag)
        with self.assertRaises(ValueError):
            create_recall_application_manually(self.db, values=self.manual_values(), user_id=1)
        self.assertEqual(self.count(RecallApplication), 2)

    def test_manual_registration_allows_deleted_application(self):
        first = create_recall_application_manually(self.db, values=self.manual_values(), user_id=1)
        bulk_soft_delete_recall_applications(self.db, ids=[first["id"]], reason="테스트 정리",
                                             reason_category="테스트 데이터", user_id=1)
        second = create_recall_application_manually(self.db, values=self.manual_values(), user_id=1)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(self.count(RecallApplication), 2)

    def test_manual_registration_review_and_required_validation_match_excel(self):
        review = create_recall_application_manually(
            self.db, values=self.manual_values(phone_original="invalid", serial_number=""), user_id=1)
        item = self.db.get(RecallApplication, review["id"])
        self.assertEqual(item.current_status, REVIEW_REQUIRED)
        self.assertIn("PHONE_INVALID", item.review_reason_codes)
        self.assertIn("SERIAL_CHECK", item.review_reason_codes)
        with self.assertRaises(ValueError):
            create_recall_application_manually(
                self.db, values=self.manual_values(customer_name=""), user_id=1)
        self.assertEqual(self.count(RecallApplication), 1)

    def test_manual_registration_detects_duplicate_serial(self):
        create_recall_application_manually(self.db, values=self.manual_values(), user_id=1)
        result = create_recall_application_manually(self.db, values=self.manual_values(
            phone_original="010-9999-8888", memo="별도 접수"), user_id=1)
        item = self.db.get(RecallApplication, result["id"])
        self.assertEqual(item.duplicate_reason, "SERIAL")

    def test_01_valid_row_registers(self):
        result = self.commit(workbook(row()))
        self.assertEqual((result.registered, self.count(RecallApplication)), (1, 1))
        self.assertEqual(self.db.scalar(select(RecallApplication)).current_status, APPLICATION_RECEIVED)

    def test_02_selected_review_row_registers(self):
        result = self.commit(workbook(row(**{"*시리얼번호": None})))
        self.assertEqual(result.registered, 1)

    def test_03_unselected_review_row_is_reported(self):
        content = workbook(
            row(),
            row(**{"성함": "김검토", "*연락처": "01033334444", "*시리얼번호": None}),
        )
        result = self.commit(content, selected=(2,))
        self.assertEqual((result.registered, result.unselected_review), (1, 1))

    def test_04_unreadable_phone_is_registered_for_review(self):
        result = self.commit(workbook(row(**{"*연락처": "invalid"})))
        self.assertEqual((result.registered, result.review, result.rejected), (1, 1, 0))
        self.assertEqual(self.db.scalar(select(RecallApplication)).current_status, REVIEW_REQUIRED)

    def test_05_duplicate_serial_is_registered_for_review(self):
        self.commit(workbook(row()))
        result = self.commit(workbook(row(**{"메모": "다른 파일", "*연락처": "01099998888"})), filename="other.xlsx")
        self.assertEqual(result.rows[0]["result"], "REGISTERED_DUPLICATE")
        self.assertEqual(self.db.scalar(select(RecallApplication).order_by(RecallApplication.id.desc())).duplicate_reason, "SERIAL")

    def test_06_duplicate_phone_is_registered_for_review(self):
        self.commit(workbook(row()))
        result = self.commit(workbook(row(**{"메모": "다른 파일", "*시리얼번호": "SER-002"})), filename="other.xlsx")
        self.assertEqual(result.rows[0]["result"], "REGISTERED_DUPLICATE")
        self.assertEqual(self.db.scalar(select(RecallApplication).order_by(RecallApplication.id.desc())).duplicate_reason, "PHONE")

    def test_07_same_file_retry_is_idempotent(self):
        content = workbook(row())
        self.commit(content)
        result = self.commit(content)
        self.assertEqual((result.registered, result.already_registered, self.count(RecallApplication)), (0, 1, 1))
        self.assertEqual(result.rows[0]["result"], "ALREADY_REGISTERED")
        existing = self.db.scalar(select(RecallApplication))
        self.assertTrue(existing.duplicate_registration_attempt)
        self.assertEqual(existing.duplicate_registration_count, 1)
        self.assertIsNotNone(existing.last_duplicate_registration_at)
        first_attempt_at = existing.last_duplicate_registration_at
        self.commit(content)
        self.assertEqual(existing.duplicate_registration_count, 2)
        self.assertGreaterEqual(existing.last_duplicate_registration_at, first_attempt_at)
        self.assertEqual(existing.current_status, APPLICATION_RECEIVED)
        self.assertFalse(existing.duplicate_flag)

    def test_soft_deleted_same_file_rows_can_register_again_without_changing_history(self):
        content = workbook(row())
        self.commit(content)
        original = self.db.scalar(select(RecallApplication))
        original_id = original.id
        original_batch_id = original.upload_batch_id
        bulk_soft_delete_recall_applications(self.db, ids=[original_id], reason="테스트 정리",
                                             reason_category="오등록", user_id=1)
        result = self.commit(content)
        self.assertEqual((result.registered, result.already_registered), (1, 0))
        self.assertEqual(self.count(RecallApplicationUploadBatch), 2)
        self.assertEqual(self.db.get(RecallApplicationUploadBatch, original_batch_id).registered_count, 1)
        self.assertTrue(self.db.get(RecallApplication, original_id).is_deleted)
        new_application = self.db.get(RecallApplication, result.rows[0]["application_id"])
        self.assertNotEqual(new_application.id, original_id)
        self.assertFalse(new_application.is_deleted)
        self.assertEqual(list_recall_applications(self.db, keyword=None, status=None,
                                                 page=1, page_size=10)["total"], 1)
        self.assertEqual(get_recall_summary(self.db)["total_count"], 1)
        retried = self.commit(content)
        self.assertEqual((retried.registered, retried.already_registered), (0, 1))
        self.assertEqual(retried.rows[0]["application_id"], new_application.id)
        self.assertEqual(self.count(RecallApplicationUploadBatch), 2)

    def test_soft_deleted_other_file_is_not_a_duplicate_candidate(self):
        self.commit(workbook(row()))
        original = self.db.scalar(select(RecallApplication))
        bulk_soft_delete_recall_applications(self.db, ids=[original.id], reason="테스트 정리",
                                             reason_category="오등록", user_id=1)
        result = self.commit(workbook(row(), [None] * len(HEADERS)), filename="retry.xlsx")
        self.assertEqual((result.registered, result.already_registered), (1, 0))
        self.assertEqual(self.db.get(RecallApplication, result.rows[0]["application_id"]).duplicate_flag, False)

    def test_deleted_ordered_application_can_be_registered_again(self):
        content = workbook(row())
        self.commit(content)
        original = self.db.scalar(select(RecallApplication))
        original.order_status = ORDER_EXPORTED
        self.db.commit()
        bulk_soft_delete_recall_applications(self.db, ids=[original.id], reason="테스트 정리",
                                             reason_category="테스트 데이터", user_id=1)
        same = self.commit(content)
        self.assertEqual((same.registered, same.already_registered), (1, 0))
        self.assertEqual(self.count(RecallApplication), 2)
        self.assertEqual(original.order_status, ORDER_EXPORTED)
        self.assertTrue(original.is_deleted)
        self.assertFalse(self.db.get(RecallApplication, same.rows[0]["application_id"]).duplicate_flag)

    def test_same_application_in_another_batch_tracks_retry_without_new_order(self):
        self.commit(workbook(row()))
        existing = self.db.scalar(select(RecallApplication))
        original_order_status = existing.order_status
        result = self.commit(workbook(row(), [None] * len(HEADERS)), filename="retry.xlsx")
        self.assertEqual((result.registered, result.already_registered, self.count(RecallApplication)), (0, 1, 1))
        self.assertEqual(result.rows[0]["application_id"], existing.id)
        self.assertEqual(existing.last_duplicate_registration_batch_id, result.batch_id)
        self.assertEqual(existing.order_status, original_order_status)
        self.assertEqual(list_recall_applications(self.db, keyword=None, status="DUPLICATE_REGISTRATION",
                                                 page=1, page_size=10)["total"], 1)
        self.assertEqual(list_recall_applications(self.db, keyword=None, status=APPLICATION_RECEIVED,
                                                 page=1, page_size=10)["total"], 1)
        detail = get_recall_application_detail(self.db, existing.id)
        self.assertTrue(detail["duplicate_registration_attempt"])
        self.assertEqual(detail["duplicate_registration_count"], 1)
        self.assertEqual(detail["last_duplicate_registration_batch_id"], result.batch_id)

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, username="tester", name="테스터", role="user", menu_permissions=["online_recall"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            listing = client.get("/online/recall/applications", params={"status": "DUPLICATE_REGISTRATION"})
            detail_response = client.get("/online/recall/applications/{}".format(existing.id))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(listing.json()["items"][0]["duplicate_registration_count"], 1)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.json()["last_duplicate_registration_batch_id"], result.batch_id)

    def test_large_retry_uses_bounded_lookup_queries_and_keeps_counts(self):
        rows = [row(**{"성함": "고객{}".format(index), "*연락처": "010{:08d}".format(index),
                       "*시리얼번호": "SER-{:04d}".format(index)}) for index in range(120)]
        first = self.commit(workbook(*rows), selected=tuple(range(2, 122)))
        self.assertEqual(first.registered, 120)
        queries = []

        def count_query(_connection, _cursor, statement, _parameters, _context, _executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                queries.append(statement)

        event.listen(self.engine, "before_cursor_execute", count_query)
        try:
            retried = self.commit(workbook(*rows, [None] * len(HEADERS)),
                                  selected=tuple(range(2, 122)), filename="retry.xlsx")
        finally:
            event.remove(self.engine, "before_cursor_execute", count_query)
        self.assertEqual((retried.registered, retried.already_registered), (0, 120))
        self.assertEqual(self.count(RecallApplication), 120)
        self.assertLessEqual(len(queries), 8)
        self.assertEqual(self.db.scalar(select(func.sum(RecallApplication.duplicate_registration_count))), 120)

    def test_legacy_formatted_phone_is_still_found_without_serial(self):
        original = row(**{"*시리얼번호": None})
        self.commit(workbook(original))
        application = self.db.scalar(select(RecallApplication))
        application.phone_normalized = "010-1111-2222"
        self.db.commit()
        result = self.commit(workbook(original, [None] * len(HEADERS)), filename="retry.xlsx")
        self.assertEqual((result.registered, result.already_registered, self.count(RecallApplication)), (0, 1, 1))

    def test_08_same_customer_in_different_file_is_not_overwritten(self):
        self.commit(workbook(row()))
        self.commit(workbook(row(**{"메모": "파일 내용 변경"})), filename="changed.xlsx")
        self.assertEqual(self.count(RecallApplication), 2)
        self.assertTrue(self.db.scalar(select(RecallApplication).order_by(RecallApplication.id.desc())).duplicate_flag)

    def test_09_missing_serial_selected_review_is_stored_as_null(self):
        self.commit(workbook(row(**{"*시리얼번호": None})))
        self.assertIsNone(self.db.scalar(select(RecallApplication)).serial_number)

    def test_10_normalized_phone_prevents_duplicate(self):
        self.commit(workbook(row(**{"*연락처": "010 1111 2222"})))
        result = self.commit(workbook(row(**{"*연락처": "010-1111-2222", "*시리얼번호": "SER-999", "메모": "changed"})))
        self.assertEqual(result.rows[0]["result"], "REGISTERED_DUPLICATE")

    def test_11_upload_batch_is_created_with_counts(self):
        self.commit(workbook(row()))
        batch = self.db.scalar(select(RecallApplicationUploadBatch))
        self.assertEqual((batch.total_rows, batch.valid_count, batch.registered_count), (1, 1, 1))

    def test_12_initial_status_history_is_created(self):
        self.commit(workbook(row()))
        history = self.db.scalar(select(RecallStatusHistory))
        self.assertEqual((history.previous_status, history.new_status, history.change_type), (None, APPLICATION_RECEIVED, "EXCEL_REGISTRATION"))

    def test_13_list_query_supports_search_status_and_pagination(self):
        self.commit(workbook(row()))
        page = list_recall_applications(self.db, keyword="11112222", status=APPLICATION_RECEIVED, page=1, page_size=10)
        self.assertEqual((page["total"], page["items"][0].customer_name), (1, "홍길동"))
        formatted_phone_page = list_recall_applications(
            self.db, keyword="010-1111-2222", status=APPLICATION_RECEIVED, page=1, page_size=10
        )
        self.assertEqual(formatted_phone_page["total"], 1)

    def test_14_summary_counts_registered_application(self):
        self.commit(workbook(row()))
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 1, "received_count": 1, "remaining_count": 1,
            "in_progress_count": 0, "shipped_count": 0,
        })

    def test_summary_workflow_tracks_current_received_count(self):
        rows = [row(**{
            "성함": "고객{}".format(index),
            "*연락처": "010{:08d}".format(index),
            "*시리얼번호": "SER-{:03d}".format(index),
        }) for index in range(20)]
        result = self.commit(workbook(*rows), selected=tuple(range(2, 22)))
        self.assertEqual(result.registered, 20)
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 20, "received_count": 20, "remaining_count": 20,
            "in_progress_count": 0, "shipped_count": 0,
        })

        application_ids = list(self.db.scalars(select(RecallApplication.id).order_by(RecallApplication.id)).all())
        for application_id in application_ids[:5]:
            change_recall_application_status(
                self.db, application_id=application_id, status=IN_PROGRESS,
                reason="진행 시작", user_id=1,
            )
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 20, "received_count": 15, "remaining_count": 15,
            "in_progress_count": 5, "shipped_count": 0,
        })

        bulk_change_recall_applications(
            self.db, ids=application_ids[:2], status=SHIPPED,
            reason="발송 완료", user_id=1,
        )
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 20, "received_count": 15, "remaining_count": 15,
            "in_progress_count": 3, "shipped_count": 2,
        })

        change_recall_application_status(
            self.db, application_id=application_ids[5], status=REVIEW_REQUIRED,
            reason="확인 필요", user_id=1,
        )
        change_recall_application_status(
            self.db, application_id=application_ids[6], status=STOPPED,
            reason="진행 중지", user_id=1,
        )
        self.assertEqual(get_recall_summary(self.db), {
            "total_count": 20, "received_count": 13, "remaining_count": 13,
            "in_progress_count": 3, "shipped_count": 2,
        })

    def test_15_unexpected_db_error_rolls_back_all_rows(self):
        content = workbook(row())
        with patch.object(self.db, "commit", side_effect=OperationalError("commit", {}, Exception("failure"))):
            with self.assertRaises(OperationalError):
                self.commit(content)
        self.assertEqual((self.count(RecallApplication), self.count(RecallStatusHistory)), (0, 0))

    def test_16_unauthorized_user_cannot_commit(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=2, username="blocked", name="차단", role="user", menu_permissions=["assets"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            response = client.post(
                "/online/recall/applications/commit",
                data={"selected_row_numbers": "[2]"},
                files={"file": ("sample.xlsx", workbook(row()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.count(RecallApplication), 0)

    def test_17_preview_api_remains_read_only(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, username="tester", name="테스터", role="user", menu_permissions=["online_recall"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            response = client.post(
                "/online/recall/applications/preview",
                files={"file": ("sample.xlsx", workbook(row()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual((self.count(RecallApplicationUploadBatch), self.count(RecallApplication)), (0, 0))

    def test_18_commit_api_registers_and_read_apis_return_it(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, username="tester", name="테스터", role="user", menu_permissions=["online_recall"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with patch("app.api.routers.recall_preview.record_audit_log", return_value=True):
            with TestClient(app) as client:
                response = client.post(
                    "/online/recall/applications/commit",
                    data={"selected_row_numbers": "[2]"},
                    files={"file": ("sample.xlsx", workbook(row()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                )
                listing = client.get("/online/recall/applications", params={"keyword": "홍길동"})
                summary = client.get("/online/recall/applications/summary")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["registered"], 1)
        self.assertEqual(listing.json()["items"][0]["customer_name"], "홍길동")
        self.assertEqual(listing.json()["items"][0]["application_date"], "2026-09-22")
        self.assertEqual(summary.json(), {
            "total_count": 1, "received_count": 1, "remaining_count": 1,
            "in_progress_count": 0, "shipped_count": 0,
        })

    def test_batch_internal_duplicate_is_registered_with_reference(self):
        content = workbook(
            row(),
            row(**{"성함": "두번째 고객", "*연락처": "010 1111 2222", "메모": "별도 신청"}),
        )
        result = self.commit(content, selected=(2, 3))
        items = list(self.db.scalars(select(RecallApplication).order_by(RecallApplication.id)).all())
        self.assertEqual((result.registered, result.normal, result.duplicate), (2, 1, 1))
        self.assertEqual(len(items), 2)
        self.assertEqual(items[1].duplicate_reason, "PHONE_AND_SERIAL")
        self.assertEqual(items[1].duplicate_reference_id, items[0].id)
        self.assertEqual(items[1].phone_normalized, "01011112222")
        self.assertEqual(list_recall_applications(self.db, keyword=None, status=None, page=1, page_size=10)["total"], 1)
        self.assertEqual(list_recall_applications(self.db, keyword=None, status=None, page=1, page_size=10,
                                                  duplicate_only=True)["total"], 1)
        all_items = list_recall_applications(self.db, keyword=None, status=None, page=1, page_size=10,
                                             include_duplicates=True)
        self.assertEqual(all_items["total"], 2)
        self.assertEqual({item.duplicate_flag for item in all_items["items"]}, {False, True})
        self.assertEqual(list_recall_applications(self.db, keyword="두번째 고객", status=APPLICATION_RECEIVED,
                                                  page=1, page_size=10, include_duplicates=True)["total"], 1)

    def test_existing_phone_and_serial_duplicate_each_register(self):
        self.commit(workbook(row()))
        self.commit(workbook(row(**{"*시리얼번호": "OTHER", "메모": "phone match"})), filename="phone.xlsx")
        self.commit(workbook(row(**{"*연락처": "00000000000", "메모": "serial match"})), filename="serial.xlsx")
        rows = list(self.db.scalars(select(RecallApplication).order_by(RecallApplication.id)).all())
        self.assertEqual([item.duplicate_reason for item in rows], [None, "PHONE", "SERIAL"])
        self.assertEqual([item.duplicate_reference_id for item in rows[1:]], [rows[0].id, rows[0].id])
        self.assertEqual(rows[2].phone_normalized, "00000000000")

    def test_invalid_phone_review_and_missing_required_do_not_block_other_rows(self):
        content = workbook(
            row(**{"*연락처": "알수없음", "*시리얼번호": "SER-A"}),
            row(**{"성함": None, "*연락처": "01022223333", "*시리얼번호": "SER-B"}),
            row(**{"성함": "정상 고객", "*연락처": "01033334444", "*시리얼번호": "SER-C"}),
        )
        result = self.commit(content, selected=(2, 3, 4))
        self.assertEqual((result.registered, result.review, result.normal, result.rejected), (2, 1, 1, 1))
        review = self.db.scalar(select(RecallApplication).where(RecallApplication.customer_name == "홍길동"))
        self.assertEqual((review.current_status, review.phone_normalized), (REVIEW_REQUIRED, ""))
        self.commit(workbook(row(**{"성함": "중복 고객", "*연락처": "010-3333-4444",
                                    "*시리얼번호": "SER-D", "메모": "다른 신청"})), filename="duplicate.xlsx")
        all_items = list_recall_applications(self.db, keyword=None, status=None, page=1, page_size=10,
                                             include_duplicates=True)["items"]
        self.assertEqual(len(all_items), 3)
        self.assertEqual(sum(item.duplicate_flag for item in all_items), 1)
        self.assertIn(REVIEW_REQUIRED, {item.current_status for item in all_items})

    def test_duplicate_resolution_api_records_history_and_releases_scm_only_after_normal(self):
        self.commit(workbook(row()))
        self.commit(workbook(row(**{"성함": "별도 고객", "메모": "별도 접수"})), filename="other.xlsx")
        duplicate = self.db.scalar(select(RecallApplication).where(RecallApplication.customer_name == "별도 고객"))
        change_recall_application_status(self.db, application_id=duplicate.id, status=IN_PROGRESS,
                                         reason="진행 시작", user_id=1)
        self.assertEqual(order_summary(self.db)["pending_count"], 0)
        with self.assertRaises(ValueError):
            preview_orders(self.db, [duplicate.id])

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, username="tester", name="테스터", role="user", menu_permissions=["online_recall"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with patch("app.api.routers.recall_preview.record_audit_log", return_value=True) as audit:
            with TestClient(app) as client:
                listing = client.get("/online/recall/applications", params={"duplicate_only": "true"})
                all_listing = client.get("/online/recall/applications", params={"include_duplicates": "true"})
                keep = client.patch("/online/recall/applications/duplicates/{}/resolve".format(duplicate.id),
                                    json={"action": "KEEP", "reason": "추가 검토 필요"})
                normal = client.patch("/online/recall/applications/duplicates/{}/resolve".format(duplicate.id),
                                      json={"action": "NORMAL", "reason": "별도 접수 확인"})
                detail = client.get("/online/recall/applications/{}".format(duplicate.id))
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["total"], 1)
        self.assertEqual(all_listing.json()["total"], 2)
        self.assertEqual(listing.json()["items"][0]["duplicate_reference"]["customer_name"], "홍길동")
        self.assertEqual((keep.status_code, keep.json()["duplicate_flag"]), (200, True))
        self.assertEqual((normal.status_code, normal.json()["duplicate_flag"]), (200, False))
        self.assertEqual(order_summary(self.db)["pending_count"], 1)
        self.assertEqual(preview_orders(self.db, [duplicate.id])["item_count"], 1)
        export_result = export_orders(self.db, ids=[duplicate.id], user_id=1)
        self.assertTrue(export_result["content"].startswith(b"PK"))
        history = list(self.db.scalars(select(RecallDuplicateResolutionHistory).order_by(RecallDuplicateResolutionHistory.id)).all())
        self.assertEqual([(item.action, item.reason, item.changed_by) for item in history],
                         [("KEEP", "추가 검토 필요", 1), ("NORMAL", "별도 접수 확인", 1)])
        self.assertEqual(len(detail.json()["duplicate_history"]), 2)
        self.assertEqual(audit.call_count, 2)
        self.assertEqual(audit.call_args.kwargs["after_data"]["reason"], "별도 접수 확인")
        self.assertNotIn("별도 고객", str(audit.call_args.kwargs))

    def test_hidden_recall_menu_blocks_commit_list_and_summary(self):
        self.db.add(MenuVisibilitySetting(menu_key="online_recall", visible=False))
        self.db.commit()
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
            id=1, username="tester", name="테스터", role="user", menu_permissions=["online_recall"]
        )
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            commit = client.post(
                "/online/recall/applications/commit",
                data={"selected_row_numbers": "[2]"},
                files={"file": ("sample.xlsx", workbook(row()), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            )
            listing = client.get("/online/recall/applications")
            summary = client.get("/online/recall/applications/summary")
        self.assertEqual([commit.status_code, listing.status_code, summary.status_code], [403, 403, 403])
        self.assertEqual(self.count(RecallApplication), 0)


if __name__ == "__main__":
    unittest.main()
