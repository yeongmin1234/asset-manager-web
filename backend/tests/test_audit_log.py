import unittest

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services.audit_log_service import ALLOWED_ACTION_TYPES, get_audit_logs, record_audit_log


def request(ip="192.168.10.20"):
    return Request({
        "type": "http", "method": "POST", "path": "/test", "query_string": b"",
        "headers": [(b"user-agent", b"Mozilla/5.0 Windows NT 10.0 Chrome/126.0")],
        "client": (ip, 1234), "server": ("test", 8010), "scheme": "http",
    })


def user():
    return User(id=7, username="admin", name="관리자", password_hash="-", role="admin", menu_permissions=[])


class AuditLogTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[AuditLog.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def record(self, action_type="create", menu_key="assets", target_type="asset"):
        return record_audit_log(
            self.db, request(), user(), action_type=action_type,
            menu_key=menu_key, menu_name="자산 관리", target_type=target_type,
            target_id=11, target_name="노트북-001", action_summary="자산을 처리했습니다.",
        )

    def test_create_update_delete_and_user_actions_are_recorded(self):
        for action in sorted(ALLOWED_ACTION_TYPES):
            self.assertTrue(self.record(action_type=action, menu_key="user_management" if action in {"activate", "deactivate", "permission_change"} else "assets", target_type="user_permission" if action == "permission_change" else "asset"))
        self.assertEqual(self.db.query(AuditLog).count(), len(ALLOWED_ACTION_TYPES))

    def test_hr_excel_import_is_one_summary_log(self):
        self.assertTrue(record_audit_log(
            self.db, request(), user(), action_type="excel_import", menu_key="hr_list",
            menu_name="인사업무 > 리스트", target_type="hr_account_import", target_id=None,
            target_name="인사업무 계정 엑셀 일괄등록",
            action_summary="엑셀 계정 92건을 등록했습니다. 중복 업데이트 5건, 건너뜀 3건.",
        ))
        self.assertEqual(self.db.query(AuditLog).count(), 1)

    def test_filters_and_pagination(self):
        self.record("update", "assets", "asset")
        result = get_audit_logs(
            self.db, keyword="노트북", username="admin", action_type="update",
            menu_key="assets", target_type="asset", access_type="internal",
            start_date=None, end_date=None, page=1, page_size=50,
        )
        self.assertEqual(result.total, 1)
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(result.items[0].username, "admin")

    def test_audit_failure_does_not_escape_business_flow(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        db = Session(engine)
        try:
            with self.assertLogs("app.services.audit_log_service", level="ERROR"):
                saved = record_audit_log(
                    db, request(), user(), action_type="create", menu_key="assets",
                    menu_name="자산 관리", target_type="asset", target_id=1,
                    target_name="노트북", action_summary="자산을 등록했습니다.",
                )
            self.assertFalse(saved)
        finally:
            db.close(); engine.dispose()


if __name__ == "__main__":
    unittest.main()
