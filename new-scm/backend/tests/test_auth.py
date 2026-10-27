import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import auth
from app.core.auth import Principal
from app.core.permissions import enforce_permission
from app.main import app


class FakeVerifier:
    def __init__(self, principal=None):
        self.principal = principal

    def verify(self, _credential):
        return self.principal


class FailingVerifier:
    def verify(self, _credential):
        raise ConnectionError("identity provider unavailable")


class AuthBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_public_status_and_diagnostics_policy(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/system/status").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/system/db-status").status_code, 403)

    def test_unconnected_auth_rejects_missing_forged_and_expired_credentials(self):
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)
        self.assertEqual(self.client.get("/api/v1/users").status_code, 401)
        for credential in ("forged-token", "expired-token"):
            response = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {credential}"},
            )
            self.assertEqual(response.status_code, 401)
            self.assertNotIn(credential, response.text)

    def test_identity_headers_are_not_trusted(self):
        response = self.client.get("/api/v1/auth/me", headers={"X-User-Id": "1", "X-Role": "admin"})
        self.assertEqual(response.status_code, 401)

    def test_verifier_failure_fails_closed_without_leaking_credential(self):
        credential = "test-secret-credential"
        with patch.object(auth, "verifier", FailingVerifier()):
            response = self.client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {credential}"},
            )
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(credential, response.text)
        self.assertNotIn("identity provider", response.text)

    def test_system_grant_is_independent_of_verified_identity(self):
        principal = Principal(subject="test-subject", name="테스트", account_type="employee", status="active")
        with patch.object(auth, "verifier", FakeVerifier(principal)):
            response = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test-only"})
        self.assertEqual(response.status_code, 403)

    def test_only_verified_principal_with_explicit_system_grant_can_read_me(self):
        principal = Principal(
            subject="test-subject", name="테스트", account_type="employee", status="active",
            action_grants=frozenset({"system.access"}),
        )
        with patch.object(auth, "verifier", FakeVerifier(principal)):
            response = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test-only"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["subject"], "test-subject")
        with patch.object(auth, "verifier", FakeVerifier(principal)):
            self.assertEqual(self.client.get("/api/v1/users", headers={"Authorization": "Bearer test-only"}).status_code, 404)

    def test_menu_action_and_admin_are_separate(self):
        principal = Principal(
            subject="test-subject", name="테스트", account_type="employee", status="active",
            menu_grants=frozenset({"sales"}),
            action_grants=frozenset({"system.access", "data.read", "admin.manage"}),
        )
        self.assertIs(enforce_permission(principal, menu="sales", action="data.read"), principal)
        for kwargs in ({"menu": "settings"}, {"action": "data.create"}, {"action": ("data.read", "bulk.change")}, {"admin": True}):
            with self.assertRaises(HTTPException) as caught:
                enforce_permission(principal, **kwargs)
            self.assertEqual(caught.exception.status_code, 403)

    def test_inactive_verifier_result_is_rejected(self):
        principal = Principal(
            subject="test-subject", name="테스트", account_type="admin", status="suspended",
            action_grants=frozenset({"system.access", "admin.manage"}),
        )
        with patch.object(auth, "verifier", FakeVerifier(principal)):
            response = self.client.get("/api/v1/auth/me", headers={"Authorization": "Bearer test-only"})
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
