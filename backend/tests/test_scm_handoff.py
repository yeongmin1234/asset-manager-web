import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.api.routers import scm_handoff


class ScmHandoffTests(unittest.TestCase):
    def setUp(self):
        scm_handoff._codes.clear()
        scm_handoff._exchange_attempts.clear()
        self.user = SimpleNamespace(id=42, role="user", menu_permissions=["scm_app"])
        self.settings = patch.object(scm_handoff.settings, "scm_handoff_key", "t" * 48)
        self.settings.start()

    def tearDown(self):
        self.settings.stop()
        scm_handoff._codes.clear()
        scm_handoff._exchange_attempts.clear()

    def test_issue_and_single_exchange(self):
        code = scm_handoff.issue(self.user)["code"]
        request = scm_handoff.ExchangeRequest(code=code, audience="new-scm")
        result = scm_handoff.exchange(request, "t" * 48)
        self.assertEqual(result, {"issuer": "asset-manager", "subject": "42", "audience": "new-scm"})
        with self.assertRaises(HTTPException) as caught:
            scm_handoff.exchange(request, "t" * 48)
        self.assertEqual(caught.exception.status_code, 401)

    def test_wrong_audience_and_key_do_not_consume_code(self):
        code = scm_handoff.issue(self.user)["code"]
        for audience, key in (("other-app", "t" * 48), ("new-scm", "wrong")):
            with self.assertRaises(HTTPException):
                scm_handoff.exchange(scm_handoff.ExchangeRequest(code=code, audience=audience), key)
        self.assertEqual(scm_handoff.exchange(scm_handoff.ExchangeRequest(code=code, audience="new-scm"), "t" * 48)["subject"], "42")

    def test_expired_forged_and_unprivileged(self):
        with self.assertRaises(HTTPException) as caught:
            scm_handoff.issue(SimpleNamespace(id=1, role="user", menu_permissions=[]))
        self.assertEqual(caught.exception.status_code, 403)
        code = scm_handoff.issue(self.user)["code"]
        with patch.object(scm_handoff, "monotonic", return_value=float("inf")):
            with self.assertRaises(HTTPException):
                scm_handoff.exchange(scm_handoff.ExchangeRequest(code=code, audience="new-scm"), "t" * 48)
        with self.assertRaises(HTTPException):
            scm_handoff.exchange(scm_handoff.ExchangeRequest(code="x" * 40, audience="new-scm"), "t" * 48)


if __name__ == "__main__":
    unittest.main()
