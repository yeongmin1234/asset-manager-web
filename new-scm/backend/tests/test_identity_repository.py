"""Isolated, disposable SQL database for the mapping and authorization boundary."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.identity import load_identity
from app.db.local_auth import principal_for
from app.core.auth import Principal
from sqlalchemy.exc import SQLAlchemyError
import re
from app.core.permissions import enforce_permission
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

    def tearDown(self):
        self.engine.dispose()

    def test_mapping_and_system_grant_revocation(self):
        principal = self.legacy_principal("asset-manager", "42")
        self.assertEqual(principal.action_grants, frozenset())
        with self.assertRaises(HTTPException):
            enforce_permission(principal)
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'action', 'system.access')"))
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'menu', '/sales')"))
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (7, 'action', 'data.read')"))
        principal = self.legacy_principal("asset-manager", "42")
        self.assertIs(enforce_permission(principal, menu="/sales", action="data.read"), principal)
        with self.assertRaises(HTTPException):
            enforce_permission(principal, action="data.create")
        with self.assertRaises(HTTPException):
            enforce_permission(principal, admin=True)
        with self.engine.begin() as db:
            db.execute(text("DELETE FROM public.scm_user_grants WHERE grant_name='system.access'"))
        with self.assertRaises(HTTPException):
            enforce_permission(self.legacy_principal("asset-manager", "42"))

    def test_missing_and_disabled_mapping_or_user(self):
        self.assertIsNone(self.legacy_principal("asset-manager", "43"))
        self.assertIsNone(self.legacy_principal("asset-manager", "042"))
        self.assertIsNone(self.legacy_principal("asset-manager", "٤٢"))
        with self.engine.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=0"))
        self.assertIsNone(self.legacy_principal("asset-manager", "42"))
        with self.engine.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=1"))
            db.execute(text("UPDATE public.users SET status='suspended' WHERE id=7"))
        self.assertIsNone(self.legacy_principal("asset-manager", "42"))

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
        principal = self.legacy_principal("asset-manager", "43")
        with self.assertRaises(HTTPException):
            enforce_permission(principal, admin=True)
        with self.engine.begin() as db:
            db.execute(text("INSERT INTO public.scm_user_grants VALUES (8, 'action', 'admin.manage')"))
        principal = self.legacy_principal("asset-manager", "43")
        self.assertIs(enforce_permission(principal, admin=True), principal)

    def test_database_failure_denies(self):
        with self.engine.begin() as db:
            db.execute(text("DROP TABLE public.scm_user_grants"))
        with self.assertRaises(SQLAlchemyError):
            self.legacy_principal("asset-manager", "42")

    def test_standalone_principal_ignores_legacy_mapping_activation(self):
        with self.engine.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=0"))
            self.assertEqual(principal_for(db, 7).subject, "7")
            self.assertIsNone(principal_for(db, 999))
            self.assertEqual(db.execute(text("SELECT count(*) FROM public.scm_identity_mappings")).scalar_one(), 1)

    def legacy_principal(self, issuer, subject):
        # Preservation test only. No legacy verifier is wired into the application.
        if not re.fullmatch(r"[1-9][0-9]*", subject):
            return None
        with self.engine.connect() as db:
            result = load_identity(db, issuer, subject)
        if result is None:
            return None
        row, grants = result
        return Principal(str(row.id), row.name, row.account_type, row.status,
                         frozenset(name for kind,name in grants if kind == "menu"),
                         frozenset(name for kind,name in grants if kind == "action"))


if __name__ == "__main__":
    unittest.main()
