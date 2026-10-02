import unittest
from unittest.mock import patch

from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.api.routers.users import create_user, update_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, normalize_menu_permissions


def make_request():
    return Request({
        "type": "http", "method": "PUT", "path": "/users/2", "headers": [],
        "client": ("127.0.0.1", 1), "server": ("test", 8010),
        "scheme": "http", "query_string": b"",
    })


class OnlineMenuPermissionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        User.__table__.create(self.engine)
        self.db = Session(self.engine)
        self.admin = User(
            username="admin", name="관리자", password_hash="-", role="admin",
            menu_permissions=[], is_active=True,
        )
        self.existing = User(
            username="existing", name="기존 사용자", password_hash="-", role="user",
            menu_permissions=["dashboard", "assets", "work_manual"], is_active=True,
        )
        self.db.add_all([self.admin, self.existing])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_new_user_defaults_keep_existing_policy_without_online_access(self):
        payload = UserCreate(username="new", name="신규", password="password123")
        self.assertEqual(payload.menu_permissions, ["dashboard", "assets"])
        self.assertNotIn("online_home", payload.menu_permissions)
        self.assertNotIn("online_recall", payload.menu_permissions)
        self.assertNotIn("online_order", payload.menu_permissions)

    def test_online_permissions_save_and_reload_without_replacing_existing_keys(self):
        original = list(self.existing.menu_permissions)
        payload = UserUpdate(
            name=self.existing.name, role="user", is_active=True,
            menu_permissions=original + ["online_home", "online_recall", "online_order"],
        )
        with patch("app.api.routers.users.record_audit_log"):
            update_user(make_request(), self.existing.id, payload, self.db, self.admin)
        self.db.expire_all()
        persisted = self.db.get(User, self.existing.id)
        self.assertEqual(persisted.menu_permissions, original + ["online_home", "online_recall", "online_order"])
        self.assertEqual(normalize_menu_permissions(original), original)

    def test_new_user_can_be_created_with_selected_online_permission_only(self):
        payload = UserCreate(
            username="new", name="신규", password="password123",
            menu_permissions=["dashboard", "assets", "online_home"],
        )
        with patch("app.api.routers.users.record_audit_log"), patch("app.api.routers.users.hash_password", return_value="hash"):
            created = create_user(make_request(), payload, self.db, self.admin)
        self.db.expire_all()
        self.assertEqual(self.db.get(User, created.id).menu_permissions, ["dashboard", "assets", "online_home"])


if __name__ == "__main__":
    unittest.main()
