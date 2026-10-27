"""Isolated, disposable SQL database for the mapping and authorization boundary."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.handoff import MappingUnavailable, resolve_principal
from app.core.permissions import enforce_permission
from app.core import scm_session
import app.main as main
from fastapi import HTTPException


class IdentityRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

        @event.listens_for(self.engine, "connect")
        def configure(dbapi_connection, _record):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
            dbapi_connection.execute("ATTACH DATABASE ':memory:' AS public")

        with self.engine.begin() as db:
            db.execute(text("CREATE TABLE public.users (id bigint PRIMARY KEY, name text, account_type text, status text)"))
            db.execute(text("""CREATE TABLE public.scm_identity_mappings (
                id integer PRIMARY KEY, issuer text NOT NULL, subject text NOT NULL,
                user_id bigint NOT NULL REFERENCES users(id), is_active boolean NOT NULL,
                UNIQUE(issuer, subject), UNIQUE(user_id))"""))
            db.execute(text("""CREATE TABLE public.scm_user_grants (
                user_id bigint NOT NULL REFERENCES users(id), grant_type text NOT NULL,
                grant_name text NOT NULL, PRIMARY KEY(user_id, grant_type, grant_name))"""))
            db.execute(text("INSERT INTO public.users VALUES (7, 'SCM 사용자', 'employee', 'active')"))
            db.execute(text("INSERT INTO public.users VALUES (8, '관리자', 'admin', 'active')"))
            db.execute(text("INSERT INTO public.scm_identity_mappings VALUES (1, 'asset-manager', '42', 7, 1)"))
        self.patch = patch("app.core.handoff._engine", return_value=self.engine)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.engine.dispose()
        scm_session._sessions.clear()

    def test_mapping_and_system_grant_revocation(self):
        principal = resolve_principal("asset-manager", "42")
        self.assertEqual(principal.action_grants, frozenset())
        with self.assertRaises(HTTPException):
            enforce_permission(principal)
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'action', 'system.access')"))
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'menu', '/sales')"))
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'action', 'data.read')"))
        principal = resolve_principal("asset-manager", "42")
        self.assertIs(enforce_permission(principal, menu="/sales", action="data.read"), principal)
        with self.assertRaises(HTTPException):
            enforce_permission(principal, action="data.create")
        with self.assertRaises(HTTPException):
            enforce_permission(principal, admin=True)
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM public.scm_user_grants WHERE grant_name='system.access'"))
        with self.assertRaises(HTTPException):
            enforce_permission(resolve_principal("asset-manager", "42"))

    def test_missing_and_disabled_mapping_or_user(self):
        self.assertIsNone(resolve_principal("asset-manager", "43"))
        self.assertIsNone(resolve_principal("asset-manager", "042"))
        self.assertIsNone(resolve_principal("asset-manager", "٤٢"))
        with self.engine.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=0"))
        self.assertIsNone(resolve_principal("asset-manager", "42"))
        with self.engine.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=1"))
            db.execute(text("UPDATE public.users SET status='suspended' WHERE id=7"))
        self.assertIsNone(resolve_principal("asset-manager", "42"))

    def test_duplicate_mapping_and_missing_user_blocked(self):
        with self.engine.begin() as db:
            with self.assertRaises(IntegrityError):
                with db.begin_nested():
                    db.execute(text("INSERT INTO public.scm_identity_mappings VALUES (2, 'asset-manager', '42', 8, 1)"))
            with self.assertRaises(IntegrityError):
                with db.begin_nested():
                    db.execute(text("INSERT INTO public.scm_identity_mappings VALUES (3, 'asset-manager', '43', 7, 1)"))
            with self.assertRaises(IntegrityError):
                with db.begin_nested():
                    db.execute(text("INSERT INTO public.scm_identity_mappings VALUES (4, 'asset-manager', '44', 999, 1)"))

    def test_admin_needs_explicit_grant(self):
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO public.scm_identity_mappings VALUES (2, 'asset-manager', '43', 8, 1)"))
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (8, 'action', 'system.access')"))
        principal = resolve_principal("asset-manager", "43")
        with self.assertRaises(HTTPException):
            enforce_permission(principal, admin=True)
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (8, 'action', 'admin.manage')"))
        principal = resolve_principal("asset-manager", "43")
        self.assertIs(enforce_permission(principal, admin=True), principal)

    def test_database_failure_denies(self):
        with self.engine.begin() as db:
            db.execute(text("DROP TABLE public.scm_user_grants"))
        with self.assertRaises(MappingUnavailable):
            resolve_principal("asset-manager", "42")

    def test_actual_repository_controls_session_and_revocation(self):
        settings = SimpleNamespace(handoff_origin="http://127.0.0.1:5173",
                                   frontend_origin="http://127.0.0.1:5174",
                                   environment="development")
        with patch.object(main, "settings", settings), patch.object(
            main, "exchange_identity", return_value=("asset-manager", "42")
        ), TestClient(main.app) as client:
            request = lambda: client.post("/api/v1/auth/handoff", json={"code": "x" * 40},
                                          headers={"Origin": settings.handoff_origin})
            self.assertEqual(request().status_code, 403)
            with self.engine.begin() as db:
                db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'action', 'system.access')"))
            response = request()
            self.assertEqual(response.status_code, 200)
            self.assertIn("scm_session", response.cookies)
            self.assertEqual(client.get("/api/v1/auth/me").status_code, 200)
            with self.engine.begin() as db:
                db.execute(text("UPDATE public.scm_identity_mappings SET is_active=0"))
            self.assertEqual(client.get("/api/v1/auth/me").status_code, 403)
            self.assertEqual(request().status_code, 403)


if __name__ == "__main__":
    unittest.main()
