import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routers.sidebar_menu_labels import update_sidebar_menu_label
from app.core.auth import require_admin
from app.db.base import Base
from app.models.sidebar_menu_label import SidebarMenuLabel
from app.models.user import User
from app.schemas.sidebar_menu_label import SidebarMenuLabelUpdate


def make_user(role="admin"):
    return User(id=1, username="tester", name="테스트", password_hash="-", role=role)


def make_request():
    return Request({
        "type": "http", "method": "PATCH", "path": "/sidebar-menu-labels/work_manual",
        "headers": [], "client": ("127.0.0.1", 1234), "server": ("testserver", 8010),
        "scheme": "http", "query_string": b"",
    })


class SidebarMenuLabelTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[SidebarMenuLabel.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_admin_updates_label_and_records_audit_changes(self):
        with patch("app.api.routers.sidebar_menu_labels.record_audit_log") as audit:
            result = update_sidebar_menu_label(
                "work_manual", SidebarMenuLabelUpdate(menu_name=" 업무 매뉴얼 "),
                make_request(), self.db, make_user(),
            )
        self.assertEqual(result.labels["work_manual"], "업무 매뉴얼")
        kwargs = audit.call_args.kwargs
        self.assertEqual(kwargs["before_data"]["menu_name"], "업무설명서")
        self.assertEqual(kwargs["after_data"]["menu_name"], "업무 매뉴얼")
        self.assertEqual(kwargs["changed_fields"], ["menu_name"])

    def test_normal_user_is_rejected_by_admin_dependency(self):
        with self.assertRaises(HTTPException) as context:
            require_admin(make_user("user"))
        self.assertEqual(context.exception.status_code, 403)

    def test_rejects_empty_too_long_and_html_names(self):
        for value in ("   ", "가" * 31, "<script>alert(1)</script>"):
            with self.assertRaises(ValidationError):
                SidebarMenuLabelUpdate(menu_name=value)

    def test_rejects_unknown_menu_key(self):
        with self.assertRaises(HTTPException) as context:
            update_sidebar_menu_label(
                "unknown", SidebarMenuLabelUpdate(menu_name="메뉴"),
                make_request(), self.db, make_user(),
            )
        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
