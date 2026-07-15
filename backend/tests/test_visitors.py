import unittest
from datetime import timedelta

from fastapi.testclient import TestClient

from app.api.routers import visitors
from app.core.auth import get_current_user
from app.main import app
from app.models.user import User


def make_user(role="admin", user_id=1, username="admin", name="더리모 관리자"):
    return User(
        id=user_id,
        username=username,
        name=name,
        password_hash="-",
        role=role,
        menu_permissions=["dashboard"],
        is_active=True,
    )


class VisitorTrackingTest(unittest.TestCase):
    def setUp(self):
        visitors._visitors.clear()
        app.dependency_overrides.clear()

    def tearDown(self):
        visitors._visitors.clear()
        app.dependency_overrides.clear()

    def test_authenticated_heartbeat_stores_server_owned_user_identity(self):
        app.dependency_overrides[get_current_user] = lambda: make_user()
        client = TestClient(app)

        ping = client.post("/visitors/ping", headers={"user-agent": "Chrome/126"})
        summary = client.get("/visitors/summary")

        self.assertEqual(ping.status_code, 200)
        self.assertEqual(summary.status_code, 200)
        item = summary.json()["visitors"][0]
        self.assertEqual(item["user_id"], 1)
        self.assertEqual(item["username"], "admin")
        self.assertEqual(item["user_name"], "더리모 관리자")
        self.assertTrue(item["ip_address"])
        self.assertEqual(item["user_agent"], "Chrome/126")

    def test_summary_is_admin_only_while_regular_user_can_ping(self):
        app.dependency_overrides[get_current_user] = lambda: make_user(
            role="user", user_id=2, username="viewer", name="일반 사용자",
        )
        client = TestClient(app)

        self.assertEqual(client.post("/visitors/ping").status_code, 200)
        self.assertEqual(client.get("/visitors/summary").status_code, 403)

    def test_legacy_ip_only_entry_remains_compatible(self):
        visitors._visitors["192.168.222.237"] = {
            "last_seen": visitors._now(),
            "user_agent": "Mozilla/5.0 Chrome/126",
        }

        item = visitors._get_active_visitors()[0]

        self.assertEqual(item["ip_address"], "192.168.222.237")
        self.assertIsNone(item["user_id"])
        self.assertIsNone(item["username"])
        self.assertIsNone(item["user_name"])

    def test_same_user_on_different_ips_counts_as_existing_ip_sessions(self):
        for ip_address in ("192.168.222.237", "192.168.222.224"):
            visitors._visitors[ip_address] = {
                "last_seen": visitors._now(),
                "user_agent": "Chrome/126",
                "user_id": 1,
                "username": "admin",
                "user_name": "더리모 관리자",
            }

        active = visitors._get_active_visitors()

        self.assertEqual(len(active), 2)
        self.assertEqual({item["ip_address"] for item in active}, {
            "192.168.222.237", "192.168.222.224",
        })

    def test_entries_older_than_180_seconds_are_removed(self):
        visitors._visitors["old"] = {
            "last_seen": visitors._now() - timedelta(seconds=181),
            "user_agent": "Chrome/126",
        }
        visitors._visitors["active"] = {
            "last_seen": visitors._now(),
            "user_agent": "Edge/126",
        }

        active = visitors._get_active_visitors()

        self.assertEqual([item["ip_address"] for item in active], ["active"])
        self.assertNotIn("old", visitors._visitors)


if __name__ == "__main__":
    unittest.main()
