import unittest
from unittest.mock import patch

from app.routers.health import database_health_check, health_check
from app.api.routers.network_status import check_target


class HealthResponseTest(unittest.TestCase):
    def test_health_returns_only_status(self):
        self.assertEqual(health_check(), {"status": "ok"})

    def test_database_health_hides_connection_error(self):
        with patch("app.routers.health.check_database_connection") as check:
            check.return_value = (False, "password=secret host=internal.example")
            self.assertEqual(database_health_check(), {"status": "error"})
            check.return_value = (True, None)
            self.assertEqual(database_health_check(), {"status": "ok"})

    def test_network_status_hides_target(self):
        target = {
            "name": "Database",
            "target": "127.0.0.1:15432",
            "type": "tcp",
            "host": "127.0.0.1",
            "port": 15432,
        }
        with patch("app.api.routers.network_status.check_tcp_target", return_value="ok"):
            item = check_target(target)
        self.assertNotIn("target", item)
        self.assertNotIn("host", item)
        self.assertNotIn("port", item)
        self.assertEqual(item["status"], "ok")


if __name__ == "__main__":
    unittest.main()
