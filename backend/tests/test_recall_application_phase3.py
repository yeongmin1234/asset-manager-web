import unittest
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.routers.recall_preview import router
from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.recall_application import (
    APPLICATION_RECEIVED,
    RecallApplication,
    RecallApplicationUploadBatch,
    RecallStatusHistory,
)
from app.models.user import User
from app.services.recall_application_excel import EXCEL_COLUMNS
from app.services.recall_application_service import (
    commit_recall_applications,
    get_recall_summary,
    list_recall_applications,
)


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
        for table in (User.__table__, RecallApplicationUploadBatch.__table__, RecallApplication.__table__, RecallStatusHistory.__table__):
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

    def test_04_error_row_is_blocked(self):
        result = self.commit(workbook(row(**{"*연락처": "invalid"})))
        self.assertEqual((result.registered, result.rejected), (0, 1))

    def test_05_duplicate_serial_is_blocked_first(self):
        self.commit(workbook(row()))
        result = self.commit(workbook(row(**{"메모": "다른 파일", "*연락처": "01099998888"})), filename="other.xlsx")
        self.assertEqual(result.rows[0]["result"], "DUPLICATE_SERIAL")

    def test_06_duplicate_phone_is_blocked(self):
        self.commit(workbook(row()))
        result = self.commit(workbook(row(**{"메모": "다른 파일", "*시리얼번호": "SER-002"})), filename="other.xlsx")
        self.assertEqual(result.rows[0]["result"], "DUPLICATE_PHONE")

    def test_07_same_file_retry_is_idempotent(self):
        content = workbook(row())
        self.commit(content)
        result = self.commit(content)
        self.assertEqual((result.registered, result.duplicate, self.count(RecallApplication)), (0, 1, 1))
        self.assertEqual(result.rows[0]["result"], "ALREADY_REGISTERED")

    def test_08_same_customer_in_different_file_is_not_overwritten(self):
        self.commit(workbook(row()))
        self.commit(workbook(row(**{"메모": "파일 내용 변경"})), filename="changed.xlsx")
        self.assertEqual(self.count(RecallApplication), 1)

    def test_09_missing_serial_selected_review_is_stored_as_null(self):
        self.commit(workbook(row(**{"*시리얼번호": None})))
        self.assertIsNone(self.db.scalar(select(RecallApplication)).serial_number)

    def test_10_normalized_phone_prevents_duplicate(self):
        self.commit(workbook(row(**{"*연락처": "010 1111 2222"})))
        result = self.commit(workbook(row(**{"*연락처": "010-1111-2222", "*시리얼번호": "SER-999", "메모": "changed"})))
        self.assertEqual(result.rows[0]["result"], "DUPLICATE_PHONE")

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

    def test_14_summary_only_increases_received(self):
        self.commit(workbook(row()))
        self.assertEqual(get_recall_summary(self.db), {"total": 0, "received": 1, "orders": 0, "shipped": 0})

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
            id=1, username="tester", name="테스터", role="user", menu_permissions=["dashboard"]
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
            id=1, username="tester", name="테스터", role="user", menu_permissions=["dashboard"]
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
        self.assertEqual(summary.json(), {"total": 0, "received": 1, "orders": 0, "shipped": 0})


if __name__ == "__main__":
    unittest.main()
