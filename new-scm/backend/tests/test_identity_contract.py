"""Existing issuer source is loaded with isolated test dependencies only.

No existing settings, credentials, running API or production database are loaded.
"""
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import StaticPool

from app.core import handoff, scm_session
import app.main as main


def isolated_issuer():
    stubs = {name: ModuleType(name) for name in
             ("app.core.auth", "app.core.config", "app.models.user")}
    stubs["app.core.auth"].get_current_user = lambda: None
    stubs["app.core.config"].settings = SimpleNamespace(scm_handoff_key="test-contract-key-" * 3)
    stubs["app.models.user"].User = type("User", (), {})
    path = Path(__file__).resolve().parents[3] / "backend/app/api/routers/scm_handoff.py"
    spec = importlib.util.spec_from_file_location("isolated_asset_handoff", path)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, stubs):
        spec.loader.exec_module(module)
    return module


class IdentityContractTests(unittest.TestCase):
    def setUp(self):
        self.issuer = isolated_issuer()
        self.user = SimpleNamespace(id=3, username="thelimo", role="employee", menu_permissions=["scm_app"])

    def exchange(self, code, *, key=None, audience="new-scm"):
        return self.issuer.exchange(self.issuer.ExchangeRequest(code=code, audience=audience),
                                    key or self.issuer.settings.scm_handoff_key)

    def test_issuer_requires_scm_permission_and_configured_key(self):
        self.user.menu_permissions = []
        with self.assertRaises(HTTPException) as rejected:
            self.issuer.issue(self.user)
        self.assertEqual(rejected.exception.status_code, 403)
        self.user.menu_permissions = ["scm_app"]
        self.issuer.settings.scm_handoff_key = ""
        with self.assertRaises(HTTPException) as rejected:
            self.issuer.issue(self.user)
        self.assertEqual(rejected.exception.status_code, 503)

    def test_wrong_key_audience_expiry_and_reuse_are_denied(self):
        code = self.issuer.issue(self.user)["code"]
        for kwargs in ({"key": "wrong-test-key" * 3}, {"audience": "other"}):
            with self.assertRaises(HTTPException):
                self.exchange(code, **kwargs)
        self.assertEqual(self.exchange(code)["subject"], "3")
        with self.assertRaises(HTTPException):
            self.exchange(code)
        code = self.issuer.issue(self.user)["code"]
        with patch.object(self.issuer, "monotonic", return_value=float("inf")), \
                self.assertRaises(HTTPException):
            self.exchange(code)

    def test_issue_exchange_mapping_grant_session_and_me(self):
        engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

        @event.listens_for(engine, "connect")
        def configure(connection, _record):
            connection.execute("ATTACH DATABASE ':memory:' AS public")

        with engine.begin() as db:
            db.execute(text("CREATE TABLE public.users (id integer PRIMARY KEY, name text, account_type text, status text)"))
            db.execute(text("CREATE TABLE public.scm_identity_mappings (issuer text, subject text, user_id integer, is_active boolean)"))
            db.execute(text("CREATE TABLE public.scm_user_grants (user_id integer, grant_type text, grant_name text)"))
            db.execute(text("INSERT INTO public.users VALUES (1, 'admin', 'admin', 'active')"))
            db.execute(text("INSERT INTO public.scm_identity_mappings VALUES ('asset-manager', '3', 1, 1)"))
        settings = SimpleNamespace(identity_base_url="http://nas-host:8010",
                                   handoff_key=self.issuer.settings.scm_handoff_key,
                                   handoff_origin="http://127.0.0.1:3010",
                                   frontend_origin="http://127.0.0.1:8011", environment="development")
        issuer = self.issuer

        class ExchangeClient:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                pass

            def post(self, url, *, headers, json):
                if url != "http://nas-host:8010/auth/scm-handoff/exchange":
                    raise AssertionError("unexpected_identity_route")
                try:
                    data = issuer.exchange(issuer.ExchangeRequest(**json), headers["X-SCM-Handoff-Key"])
                    return SimpleNamespace(status_code=200, json=lambda: data)
                except HTTPException as exc:
                    return SimpleNamespace(status_code=exc.status_code)

        try:
            with patch.object(handoff, "_engine", return_value=engine), \
                    patch.object(handoff, "get_settings", return_value=settings), \
                    patch.object(main, "settings", settings), TestClient(main.app) as client:
                with patch.object(handoff.httpx, "Client", return_value=ExchangeClient()):
                    code = issuer.issue(self.user)["code"]
                    denied = client.post("/api/v1/auth/handoff", json={"code": code, "user_id": 1},
                                         headers={"Origin": settings.handoff_origin})
                    self.assertEqual(denied.status_code, 403)
                    self.assertNotIn("scm_session", denied.cookies)
                    with engine.begin() as db:
                        db.execute(text("INSERT INTO public.scm_user_grants VALUES (1, 'action', 'system.access')"))
                    code = issuer.issue(self.user)["code"]
                    response = client.post("/api/v1/auth/handoff", json={"code": code},
                                           headers={"Origin": settings.handoff_origin})
                    self.assertEqual(response.status_code, 200)
                    self.assertIn("scm_session", response.cookies)
                    replay = client.post("/api/v1/auth/handoff", json={"code": code},
                                         headers={"Origin": settings.handoff_origin})
                    self.assertEqual(replay.status_code, 401)
                me = client.get("/api/v1/auth/me")
                self.assertEqual(me.status_code, 200)
                self.assertEqual(me.json()["data"]["subject"], "asset-manager:3")
                self.assertEqual(me.json()["data"]["action_grants"], ["system.access"])
                with engine.begin() as db:
                    db.execute(text("DELETE FROM public.scm_user_grants"))
                self.assertEqual(client.get("/api/v1/auth/me").status_code, 403)
        finally:
            scm_session._sessions.clear()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
