"""Deployment boundaries: reject write roles, URL overrides and arbitrary HTTP."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from sqlalchemy.dialects.postgresql.psycopg import PGDialect_psycopg

from app.core import handoff
from app.db import database


class DeploymentBoundaryTests(unittest.TestCase):
    def tearDown(self):
        database._engine.cache_clear()

    def test_database_rejects_wrong_role_database_driver_and_override_parameters(self):
        rejected = (
            "postgresql+psycopg://postgres:test@127.0.0.1/new_scm_dev",
            "postgresql+psycopg://new_scm_ro:test@127.0.0.1/asset_manager_prod",
            "postgresql://new_scm_ro:test@127.0.0.1/new_scm_dev",
            "postgresql+psycopg://new_scm_ro:test@127.0.0.1/new_scm_dev?dbname=asset_manager_prod",
            "postgresql+psycopg://new_scm_ro:test@127.0.0.1/new_scm_dev?user=postgres",
            "postgresql+psycopg://new_scm_ro:test@127.0.0.1/new_scm_dev?service=other",
            "invalid-url",
        )
        for url in rejected:
            with self.subTest(case=rejected.index(url)), self.assertRaises(database.DatabaseUnavailable):
                database._validated_url(url)

    def test_unix_route_preserves_credentials_and_readonly_options(self):
        url = "postgresql+psycopg://new_scm_ro:test-only@172.17.0.2:5432/new_scm_dev"
        with patch.object(database, "get_settings", return_value=SimpleNamespace(database_url=url)), \
                patch.dict(os.environ, {"SCM_DATABASE_SOCKET_DIR": "/srv/new-scm/db-socket"}), \
                patch.object(database, "create_engine") as create:
            database._engine()
        target = create.call_args.args[0]
        self.assertIsNone(target.host)
        self.assertEqual(target.port, 15432)
        self.assertEqual(dict(target.query), {"host": "/srv/new-scm/db-socket"})
        self.assertEqual((target.username, target.password, target.database),
                         ("new_scm_ro", "test-only", "new_scm_dev"))
        self.assertIn("default_transaction_read_only=on", create.call_args.kwargs["connect_args"]["options"])
        _, parameters = PGDialect_psycopg().create_connect_args(target)
        self.assertEqual((parameters["host"], parameters["port"], parameters["dbname"], parameters["user"]),
                         ("/srv/new-scm/db-socket", 15432, "new_scm_dev", "new_scm_ro"))

    def test_arbitrary_unix_path_is_rejected(self):
        with patch.object(database, "get_settings", return_value=SimpleNamespace(
            database_url="postgresql+psycopg://new_scm_ro:test@localhost/new_scm_dev"
        )), patch.dict(os.environ, {"SCM_DATABASE_SOCKET_DIR": "/var/run/postgresql"}), \
                self.assertRaises(database.DatabaseUnavailable):
            database._engine()

    def test_only_exact_pinned_gateway_http_address_is_allowed(self):
        for address in ("http://172.17.0.1:8010", "http://nas-host:8011", "http://nas-host:8010/other",
                        "http://nas-host:8010?x=y", "http://nas-host:8010#fragment", "http://other:8010"):
            with patch.object(handoff, "get_settings", return_value=SimpleNamespace(
                identity_base_url=address, handoff_key="test-only-" * 5
            )), patch.object(handoff.httpx, "Client") as client:
                with self.assertRaises(handoff.HandoffRejected):
                    handoff.exchange_identity("test-code-" * 5)
                client.assert_not_called()

    def test_pinned_gateway_exchange_does_not_follow_redirects_or_proxy_environment(self):
        with patch.object(handoff, "get_settings", return_value=SimpleNamespace(
            identity_base_url="http://nas-host:8010", handoff_key="test-only-" * 5
        )), patch.object(handoff.httpx, "Client") as client:
            client.return_value.__enter__.return_value.post.return_value = SimpleNamespace(
                status_code=200, json=lambda: {"issuer": "asset-manager", "subject": "3", "audience": "new-scm"})
            self.assertEqual(handoff.exchange_identity("test-code-" * 5), ("asset-manager", "3"))
        self.assertEqual(client.call_args.kwargs, {"timeout": 3.0, "follow_redirects": False, "trust_env": False})


if __name__ == "__main__":
    unittest.main()
