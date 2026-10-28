import contextlib
import io
import os
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core import auth_routes, local_auth
from app.core.auth import Principal
from app.core.permissions import require_permission
from app.db.local_auth import AuthUnavailable, validated_url
from app.main import app


class IndependentAuthTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.config = patch.object(auth_routes, "get_settings", return_value=SimpleNamespace(
            environment="development", frontend_origin="http://127.0.0.1:8011"))
        self.config.start()
        self.origin = {"Origin": "http://127.0.0.1:8011"}

    def tearDown(self):
        self.config.stop()
        self.client.close()
        app.dependency_overrides.clear()

    def test_direct_login_sets_opaque_cookie_and_never_returns_token(self):
        with patch.object(local_auth, "login", return_value="x" * 64) as login, patch("httpx.Client") as external:
            response = self.client.post("/api/v1/auth/login", headers=self.origin,
                                        json={"username": "operator", "password": "test-only-password"})
        self.assertEqual(response.status_code, 200)
        cookie = response.headers["set-cookie"].lower()
        for value in ("httponly", "samesite=strict", "path=/api/v1", "max-age=1800"):
            self.assertIn(value, cookie)
        self.assertNotIn("secure;", cookie)
        self.assertNotIn("x" * 64, response.text)
        external.assert_not_called()
        login.assert_called_once()

    def test_production_cookie_requires_https_origin_and_secure_flag(self):
        with patch.object(auth_routes, "get_settings", return_value=SimpleNamespace(
                environment="production", frontend_origin="https://scm.example")), \
                patch.object(local_auth, "login", return_value="x" * 64):
            response = self.client.post("/api/v1/auth/login", headers={"Origin": "https://scm.example"},
                                        json={"username": "operator", "password": "test-only-password"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Secure", response.headers["set-cookie"])

    def test_login_rejects_missing_cross_site_private_http_and_null_origin_before_db(self):
        for origin in ({}, {"Origin": "null"}, {"Origin": "http://asset.example"}):
            with patch.object(local_auth, "login") as login:
                response = self.client.post("/api/v1/auth/login", headers=origin,
                                            json={"username": "operator", "password": "test-only-password"})
            self.assertEqual(response.status_code, 403)
            login.assert_not_called()
        with patch.object(auth_routes, "get_settings", return_value=SimpleNamespace(
                environment="development", frontend_origin="http://192.168.222.210:8011")), \
                patch.object(local_auth, "login") as login:
            self.assertEqual(self.client.post("/api/v1/auth/login", headers={"Origin": "http://192.168.222.210:8011"},
                json={"username": "operator", "password": "test-only-password"}).status_code, 403)
            login.assert_not_called()

    def test_unexpected_auth_failure_never_returns_details(self):
        for error, status, code in ((RuntimeError("private-test-db-url"), 503, "auth_unavailable"),
                                   (local_auth.AuthFailure("invalid_credentials"), 401, "invalid_credentials"),
                                   (local_auth.AuthFailure("login_rate_limited", 429), 429, "login_rate_limited")):
            with patch.object(local_auth, "login", side_effect=error):
                response = self.client.post("/api/v1/auth/login", headers=self.origin,
                                            json={"username": "operator", "password": "test-only-password"})
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json()["error"]["code"], code)
            self.assertNotIn("private-test-db-url", response.text)
            self.assertNotIn("test-only-password", response.text)
            self.assertEqual(response.headers["cache-control"], "no-store")
            if status == 429:
                self.assertEqual(response.headers["retry-after"], "900")

    def test_logout_revokes_server_token_and_deletes_cookie(self):
        self.client.cookies.set("scm_session", "x" * 64)
        with patch.object(local_auth, "logout") as revoke:
            response = self.client.post("/api/v1/auth/logout", headers=self.origin)
        self.assertEqual(response.status_code, 200)
        revoke.assert_called_once_with("x" * 64)
        self.assertIn("Max-Age=0", response.headers["set-cookie"])

    def test_handoff_is_absent_from_routes_and_openapi(self):
        paths = app.openapi()["paths"]
        self.assertNotIn("/api/v1/auth/handoff", paths)
        self.assertEqual(self.client.post("/api/v1/auth/handoff", json={"code": "test-only"}).status_code, 401)

    def test_default_bearer_and_forged_identity_headers_cannot_authenticate(self):
        self.assertEqual(self.client.get("/api/v1/auth/me", headers={
            "Authorization": "Bearer fake", "X-User-Id": "1", "X-Role": "admin"}).status_code, 401)

    def test_password_hash_is_argon2id_unique_salted_and_policy_bounded(self):
        first = local_auth.hash_password("test-only-passphrase")
        second = local_auth.hash_password("test-only-passphrase")
        self.assertTrue(first.startswith("$argon2id$"))
        self.assertNotEqual(first, second)
        self.assertTrue(local_auth.hasher.verify(first, "test-only-passphrase"))
        for password in ("short", "x" * 257, ""):
            with self.assertRaises(local_auth.AuthFailure):
                local_auth.hash_password(password)

    def test_writer_url_rejects_readonly_superuser_wrong_db_and_overrides(self):
        valid = "postgresql+psycopg://new_scm_auth:test-only@localhost/new_scm_dev"
        self.assertEqual(validated_url(valid).username, "new_scm_auth")
        for url in (valid.replace("new_scm_auth", "postgres"), valid.replace("new_scm_auth", "new_scm_ro"),
                    valid.replace("new_scm_dev", "asset_manager_prod"), valid + "?user=postgres", "invalid"):
            with self.assertRaises(AuthUnavailable):
                validated_url(url)

    def test_writer_socket_route_preserves_separate_identity_and_hides_parameters(self):
        from app.db import local_auth as database
        database.engine.cache_clear()
        settings = SimpleNamespace(
            database_url="postgresql+psycopg://new_scm_ro:test-only@localhost:15432/new_scm_dev",
            auth_database_url="postgresql+psycopg://new_scm_auth:test-only@localhost:15432/new_scm_dev")
        try:
            with patch.object(database, "get_settings", return_value=settings), \
                    patch.dict(os.environ, {"SCM_DATABASE_SOCKET_DIR": "/srv/new-scm/db-socket"}), \
                    patch.object(database, "create_engine") as create:
                database.engine()
            target = create.call_args.args[0]
            self.assertEqual((target.username, target.database, target.port), ("new_scm_auth", "new_scm_dev", 15432))
            self.assertEqual(dict(target.query), {"host": "/srv/new-scm/db-socket"})
            self.assertTrue(create.call_args.kwargs["hide_parameters"])
            self.assertNotIn("default_transaction_read_only=on", create.call_args.kwargs["connect_args"]["options"])
        finally:
            database.engine.cache_clear()

    def test_json_validation_does_not_echo_password_or_accept_privilege_fields(self):
        response = self.client.post("/api/v1/auth/login", headers=self.origin,
            json={"username": "operator", "password": "test-only-password", "account_type": "admin"})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn("test-only-password", response.text)

    def test_non_admin_cannot_manage_credentials(self):
        from app.core.auth import get_current_principal
        app.dependency_overrides[get_current_principal] = lambda: Principal("2", "Employee", "employee", "active",
            action_grants=frozenset({"system.access", "admin.manage"}))
        with patch.object(local_auth, "list_users") as users, patch.object(local_auth, "set_credentials") as save:
            self.assertEqual(self.client.get("/api/v1/admin/auth/users").status_code, 403)
            self.assertEqual(self.client.post("/api/v1/admin/auth/users/1/credentials", headers=self.origin,
                                              json={"enabled": False}).status_code, 403)
        users.assert_not_called(); save.assert_not_called()

    def test_initial_admin_cli_does_not_run_without_interactive_operator(self):
        from app.core import provision_auth
        with patch.object(provision_auth.sys.stdin, "isatty", return_value=False), \
                patch.object(provision_auth, "set_credentials") as save, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(provision_auth.main(["--user-id", "1", "--initial-admin"]), 1)
        save.assert_not_called()
        self.assertEqual(out.getvalue(), "FAIL scm_credentials_provisioning_failed\n")

    def test_runtime_roles_cannot_be_used_as_alembic_migration_owner(self):
        path = Path(__file__).resolve().parents[1] / "alembic/env.py"
        spec = importlib.util.spec_from_file_location("test_scm_migration_env", path)
        module = importlib.util.module_from_spec(spec)
        with patch("alembic.context.is_offline_mode", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "Offline SCM migration is disabled"):
                spec.loader.exec_module(module)
        for role in ("new_scm_ro", "new_scm_auth", "new_scm_reader"):
            with patch.dict(os.environ, {"SCM_MIGRATION_ROLE": role,
                "SCM_MIGRATION_DATABASE_URL": f"postgresql+psycopg://{role}:test-only@127.0.0.1:5432/new_scm_dev"}), \
                    self.assertRaisesRegex(RuntimeError, "Dedicated SCM migration credentials are required"):
                module.migration_url()

    def test_writer_rejects_different_target_and_unapproved_unix_directory_before_connect(self):
        from app.db import local_auth as database
        reader = "postgresql+psycopg://new_scm_ro:test-only@localhost:15432/new_scm_dev"
        for host, socket in (("different-host", ""), ("localhost", "/var/run/postgresql")):
            database.engine.cache_clear()
            settings = SimpleNamespace(database_url=reader,
                auth_database_url=f"postgresql+psycopg://new_scm_auth:test-only@{host}:15432/new_scm_dev")
            try:
                with patch.object(database, "get_settings", return_value=settings), \
                        patch.dict(os.environ, {"SCM_DATABASE_SOCKET_DIR": socket}), \
                        patch.object(database, "create_engine") as create, self.assertRaises(AuthUnavailable):
                    database.engine()
                create.assert_not_called()
            finally:
                database.engine.cache_clear()

    def test_migration_target_rejects_query_overrides_before_connecting(self):
        path = Path(__file__).resolve().parents[1] / "alembic/env.py"
        spec = importlib.util.spec_from_file_location("test_scm_migration_target", path)
        module = importlib.util.module_from_spec(spec)
        with patch("alembic.context.is_offline_mode", return_value=True):
            with self.assertRaises(RuntimeError):
                spec.loader.exec_module(module)
        base = "postgresql+psycopg://scm_migrator:test-only@127.0.0.1:5432/new_scm_dev"
        for url in (base + "?dbname=asset_manager_prod", base + "?user=postgres", base + "?service=other",
                    base.replace("postgresql+psycopg", "postgresql")):
            with patch.dict(os.environ, {"SCM_MIGRATION_ROLE": "scm_migrator", "SCM_MIGRATION_DATABASE_URL": url}), \
                    self.assertRaisesRegex(RuntimeError, "SCM migration target or role rejected"):
                module.migration_url()

    def test_schema_checks_preserve_literal_whitespace_and_expiry_numeric_types(self):
        from app.db.auth_policy import _check_expression
        valid = _check_expression("(password_hash)::text ~~ '$argon2id$%'::text", True)
        self.assertEqual(valid, "password_hash~~'$argon2id$%'")
        self.assertNotEqual(valid, _check_expression("password_hash ~~ ' $argon2id$% '::text", True))
        self.assertNotEqual(_check_expression("expires_at > created_at"),
                            _check_expression("expires_at::text > created_at::text"))

    @unittest.skipUnless(os.name == "posix", "POSIX backup protection required")
    def test_migration_backup_must_be_owned_private_and_not_symlink(self):
        import tempfile
        path = Path(__file__).resolve().parents[1] / "alembic/env.py"
        spec = importlib.util.spec_from_file_location("test_scm_migration_backup", path)
        module = importlib.util.module_from_spec(spec)
        with patch("alembic.context.is_offline_mode", return_value=True):
            with self.assertRaises(RuntimeError):
                spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix="scm-backup-guard-") as folder:
            backup = Path(folder) / "fixture.dump"; backup.write_bytes(b"PGDMP-fixture-only"); backup.chmod(0o600)
            values = {"SCM_MIGRATION_ROLE": "scm_migrator",
                "SCM_MIGRATION_DATABASE_URL": "postgresql+psycopg://scm_migrator:test-only@127.0.0.1:5432/new_scm_dev",
                "SCM_MIGRATION_BACKUP_PATH": str(backup)}
            with patch.dict(os.environ, values):
                self.assertEqual(module.migration_url()[1], "scm_migrator")
                backup.chmod(0o644)
                with self.assertRaisesRegex(RuntimeError, "SCM backup owner and mode 600 required"):
                    module.migration_url()
                backup.chmod(0o600)
                link = Path(folder) / "linked.dump"; link.symlink_to(backup)
                os.environ["SCM_MIGRATION_BACKUP_PATH"] = str(link)
                with self.assertRaisesRegex(RuntimeError, "Verified SCM backup artifact is required"):
                    module.migration_url()


if __name__ == "__main__":
    unittest.main()
