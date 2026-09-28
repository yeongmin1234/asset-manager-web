import unittest
from unittest.mock import patch

from fastapi import HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routers.menu_visibility import get_menu_visibility, update_menu_visibility
from app.core.auth import require_admin
from app.db.base import Base
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.user import User
from app.schemas.menu_visibility import MenuVisibilityUpdate


def make_user(role="admin"):
    return User(id=1, username="tester", name="테스트", password_hash="-", role=role)


def make_request():
    return Request({"type": "http", "method": "PATCH", "path": "/menu-visibility/statistics", "headers": [], "client": ("127.0.0.1", 1), "server": ("test", 8010), "scheme": "http", "query_string": b""})


class MenuVisibilityTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine, tables=[MenuVisibilitySetting.__table__])
        self.db = Session(self.engine)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_missing_settings_default_to_visible(self):
        result = get_menu_visibility(self.db)
        self.assertTrue(all(result.visibility.values()))

    def test_admin_can_hide_and_show_menu_with_audit_log(self):
        with patch("app.api.routers.menu_visibility.record_audit_log") as audit:
            hidden = update_menu_visibility("statistics", MenuVisibilityUpdate(visible=False), make_request(), self.db, make_user())
            shown = update_menu_visibility("statistics", MenuVisibilityUpdate(visible=True), make_request(), self.db, make_user())
        self.assertFalse(hidden.visibility["statistics"])
        self.assertTrue(shown.visibility["statistics"])
        self.assertEqual(audit.call_count, 2)
        first = audit.call_args_list[0].kwargs
        self.assertEqual(first["before_data"]["visible"], True)
        self.assertEqual(first["after_data"]["visible"], False)
        self.assertEqual(first["changed_fields"], ["visible"])

    def test_online_visibility_is_independent_of_existing_setting(self):
        self.db.add(MenuVisibilitySetting(menu_key="statistics", visible=False))
        self.db.commit()
        with patch("app.api.routers.menu_visibility.record_audit_log"):
            hidden = update_menu_visibility("online_recall", MenuVisibilityUpdate(visible=False), make_request(), self.db, make_user())
            shown = update_menu_visibility("online_home", MenuVisibilityUpdate(visible=True), make_request(), self.db, make_user())
        self.assertFalse(hidden.visibility["online_recall"])
        self.assertTrue(shown.visibility["online_home"])
        self.assertFalse(shown.visibility["statistics"])

    def test_always_visible_menus_cannot_be_hidden(self):
        for menu_key in ("dashboard", "assets", "settings"):
            with self.assertRaises(HTTPException) as context:
                update_menu_visibility(menu_key, MenuVisibilityUpdate(visible=False), make_request(), self.db, make_user())
            self.assertEqual(context.exception.status_code, 400)

    def test_unknown_menu_is_rejected_and_normal_user_is_forbidden(self):
        with self.assertRaises(HTTPException) as unknown:
            update_menu_visibility("unknown", MenuVisibilityUpdate(visible=False), make_request(), self.db, make_user())
        self.assertEqual(unknown.exception.status_code, 404)
        with self.assertRaises(HTTPException) as forbidden:
            require_admin(make_user("user"))
        self.assertEqual(forbidden.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
