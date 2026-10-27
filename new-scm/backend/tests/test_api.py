import unittest

from app.db.database import DatabaseUnavailable, _validated_url
from app.main import database_status, health, system_status


class Stage3ApiTests(unittest.TestCase):
    def test_health_is_independent_of_database(self):
        self.assertEqual(
            health(),
            {"ok": True, "data": {"service": "new-scm", "status": "up"}, "error": None},
        )

    def test_status_does_not_probe_database(self):
        self.assertEqual(system_status()["data"]["database"], "not_checked")

    def test_db_status_requires_key(self):
        self.assertEqual(database_status(None).status_code, 403)

    def test_other_database_is_rejected_before_connect(self):
        with self.assertRaisesRegex(DatabaseUnavailable, "database_target_rejected"):
            _validated_url("postgresql+psycopg://example:example@127.0.0.1/other_database")


if __name__ == "__main__":
    unittest.main()
