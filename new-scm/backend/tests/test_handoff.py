import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.auth import Principal
from app.core import scm_session
from app.core import handoff

main = importlib.import_module("app.main")


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)
        self.origin = {"Origin": "http://127.0.0.1:5173"}
        self.config = patch.object(main, "settings", SimpleNamespace(
            handoff_origin="http://127.0.0.1:5173",
            frontend_origin="http://127.0.0.1:5174",
            environment="development",
        ))
        self.config.start()

    def tearDown(self):
        self.config.stop()
        self.client.close()
        scm_session._sessions.clear()

    def test_unmapped_identity_denied_and_no_cookie(self):
        with patch.object(main, "exchange_identity", return_value=("asset-manager", "42")), patch.object(main, "resolve_principal", return_value=None):
            response = self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}, headers=self.origin)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("scm_session", response.cookies)

    def test_missing_grant_denied(self):
        principal = Principal("asset-manager:42", "테스트", "employee", "active")
        with patch.object(main, "exchange_identity", return_value=("asset-manager", "42")), patch.object(main, "resolve_principal", return_value=principal):
            response = self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}, headers=self.origin)
        self.assertEqual(response.status_code, 403)

    def test_database_failure_denies_without_cookie_or_details(self):
        with patch.object(main, "exchange_identity", return_value=("asset-manager", "42")), patch.object(
            main, "resolve_principal", side_effect=main.MappingUnavailable("private database detail")
        ):
            response = self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}, headers=self.origin)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("scm_session", response.cookies)
        self.assertNotIn("private database detail", response.text)

    def test_verified_identity_issues_session_and_rechecks_mapping(self):
        principal = Principal("asset-manager:42", "테스트", "employee", "active", action_grants=frozenset({"system.access"}))
        with patch.object(main, "exchange_identity", return_value=("asset-manager", "42")), patch.object(main, "resolve_principal", return_value=principal):
            response = self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}, headers=self.origin)
        self.assertEqual(response.status_code, 200)
        self.assertIn("httponly", response.headers["set-cookie"].lower())
        with patch("app.core.handoff.resolve_principal", return_value=principal):
            self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 200)
        with patch("app.core.handoff.resolve_principal", return_value=None):
            self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 403)

    def test_untrusted_origin_and_provider_failure(self):
        self.assertEqual(self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}).status_code, 403)
        with patch.object(main, "exchange_identity", side_effect=main.HandoffRejected()):
            self.assertEqual(self.client.post("/api/v1/auth/handoff", json={"code": "x" * 40}, headers=self.origin).status_code, 401)

    def test_identity_exchange_rejects_untrusted_transport_and_forged_subject(self):
        with patch.object(handoff, "get_settings", return_value=SimpleNamespace(identity_base_url="http://external.example", handoff_key="t" * 48)):
            with self.assertRaises(handoff.HandoffRejected):
                handoff.exchange_identity("x" * 40)
        fake_client = SimpleNamespace(post=lambda *_args, **_kwargs: SimpleNamespace(
            status_code=200, json=lambda: {"issuer": "asset-manager", "subject": "forged", "audience": "new-scm"}
        ))
        # Special methods must live on a class for Python's context-manager lookup.
        class ClientContext:
            def __enter__(self):
                return fake_client
            def __exit__(self, *_args):
                return None
        with patch.object(handoff, "get_settings", return_value=SimpleNamespace(identity_base_url="http://127.0.0.1:8010", handoff_key="t" * 48)), patch.object(handoff.httpx, "Client", return_value=ClientContext()):
            with self.assertRaises(handoff.HandoffRejected):
                handoff.exchange_identity("x" * 40)

    def test_session_expiry(self):
        token = scm_session.create("asset-manager", "42")
        self.assertEqual(scm_session.lookup(token), ("asset-manager", "42"))
        with patch.object(scm_session, "monotonic", return_value=float("inf")):
            self.assertIsNone(scm_session.lookup(token))
        self.assertIsNone(scm_session.lookup(token))

    def test_scm_logout_revokes_cookie(self):
        token = scm_session.create("asset-manager", "42")
        self.client.cookies.set("scm_session", token)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers={"Origin": "http://127.0.0.1:5174"}).status_code, 200)
        self.assertIsNone(scm_session.lookup(token))


if __name__ == "__main__":
    unittest.main()
