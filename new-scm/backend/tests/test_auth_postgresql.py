"""Opt-in real PostgreSQL tests. ONLY an isolated local Unix socket is accepted.

The runner creates a disposable network=none PostgreSQL cluster under /tmp.
No NAS endpoint, TCP connection, existing database or deployment is accepted.
"""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError

from app.core import local_auth, auth_routes
from app.db.auth_policy import verify_auth_connection
from app.main import app
from migration_fixtures import backup, fingerprint, fixture_container, restore


@unittest.skipUnless(os.getenv("SCM_TEST_PG_SOCKET"), "isolated local PostgreSQL socket not supplied")
class StandalonePostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        socket = Path(os.environ["SCM_TEST_PG_SOCKET"]).resolve(strict=True)
        if socket.parent != Path("/tmp") or not socket.name.startswith("scm-standalone-pg-"):
            raise RuntimeError("test_database_socket_rejected")
        def connection(role):
            return create_engine(URL.create("postgresql+psycopg", username=role, password="test-only",
                database="new_scm_dev", query={"host": str(socket)}), hide_parameters=True,
                pool_size=4, max_overflow=0, connect_args={"options": "-c statement_timeout=5000"})
        cls.owner, cls.writer, cls.reader = (connection(role) for role in ("postgres", "new_scm_auth", "new_scm_ro"))
        if os.getenv("SCM_TEST_PG_CONTAINER"):
            fixture_container()
        with cls.owner.begin() as db:
            if tuple(db.execute(text("SELECT current_database(), current_user")).one()) != ("new_scm_dev", "postgres"):
                raise RuntimeError("test_database_identity_rejected")
            if db.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one() != 0:
                raise RuntimeError("test_database_must_be_empty")
            db.execute(text("CREATE ROLE new_scm_ro LOGIN NOINHERIT"))
            db.execute(text("ALTER ROLE new_scm_ro SET default_transaction_read_only=on"))
            db.execute(text("CREATE ROLE new_scm_auth LOGIN NOINHERIT"))
            db.execute(text("CREATE TABLE public.users (id bigint PRIMARY KEY, username varchar(50) UNIQUE NOT NULL, "
                            "name varchar(100) NOT NULL, account_type varchar(20) NOT NULL, status varchar(20) NOT NULL, "
                            "password_hash varchar(512) NOT NULL)"))
            db.execute(text("CREATE TABLE public.alembic_version (version_num varchar(32) PRIMARY KEY)"))
            db.execute(text("INSERT INTO public.alembic_version VALUES ('20261027_0013')"))
            for index in range(50):
                db.execute(text("CREATE TABLE public.test_business_%d (id bigint PRIMARY KEY)" % index))
                db.execute(text("INSERT INTO public.test_business_%d VALUES (1),(2)" % index))
            db.execute(text("INSERT INTO public.users VALUES "
                "(1,'admin-local','SCM Admin','admin','active','legacy-hash-preserved'),"
                "(2,'employee-local','SCM User','employee','active','legacy-hash-preserved')"))
            cls.migrate(db, "20261027_0013_scm_identity_grants.py")
            db.execute(text("INSERT INTO public.scm_identity_mappings "
                "(issuer,subject,user_id,is_active,approved_by,approved_at) VALUES ('asset-manager','3',1,true,1,now())"))
            db.execute(text("GRANT SELECT ON ALL TABLES IN SCHEMA public TO new_scm_ro"))
            db.execute(text("INSERT INTO public.scm_user_grants (user_id,grant_type,grant_name,approved_by) "
                            "VALUES (1,'action','system.access',1),(1,'action','admin.manage',1)"))
            cls.before_users = db.execute(text("SELECT * FROM public.users ORDER BY id")).all()
            cls.before_mappings = db.execute(text("SELECT * FROM public.scm_identity_mappings")).all()
        with cls.owner.connect() as db:
            cls.before_snapshot = fingerprint(db)
            cls.public_before = fingerprint(db, ignore_revision_data=True, include_auth=False, exclude_auth_role=True)
        import preflight
        with patch("sqlalchemy.create_engine", return_value=cls.reader) as factory:
            try:
                preflight.runtime_checks("postgresql+psycopg://new_scm_ro:test-only@localhost/new_scm_dev",
                                         phase="pre-migration")
            except preflight.Pending as exc:
                if str(exc) != "auth_migration_required":
                    raise
            else:
                raise RuntimeError("pre_migration_must_remain_pending")
            if factory.call_count != 1:
                raise RuntimeError("pre_migration_must_not_connect_auth_writer")
        cls.before_archive = backup() if os.getenv("SCM_TEST_PG_CONTAINER") else None
        if cls.before_archive is not None:
            from alembic import command
            from alembic.config import Config
            root = Path(__file__).resolve().parents[2]
            with tempfile.TemporaryDirectory(prefix="scm-migration-backup-") as folder:
                artifact = Path(folder) / "fixture.dump"
                artifact.write_bytes(cls.before_archive); artifact.chmod(0o600)
                settings = Config(str(root / "backend/alembic.ini"))
                settings.set_main_option("script_location", str(root / "backend/alembic"))
                settings.set_main_option("prepend_sys_path", str(root / "backend"))
                # Only the connection factory is redirected to the already-guarded
                # local Unix fixture. Production URL/backup/identity guards run.
                with patch.dict(os.environ, {"SCM_MIGRATION_ROLE": "postgres",
                    "SCM_MIGRATION_DATABASE_URL": "postgresql+psycopg://postgres:test-only@127.0.0.1:5432/new_scm_dev",
                    "SCM_MIGRATION_BACKUP_PATH": str(artifact)}), patch("sqlalchemy.create_engine", return_value=cls.owner):
                    command.upgrade(settings, "20261028_0014")
        else:
            with cls.owner.begin() as db:
                cls.migrate(db, "20261028_0014_standalone_auth.py")
                db.execute(text("UPDATE public.alembic_version SET version_num='20261028_0014'"))
        with cls.owner.connect() as db:
            if cls.public_before != fingerprint(db, ignore_revision_data=True, include_auth=False, exclude_auth_role=True):
                raise RuntimeError("migration_changed_existing_public_schema_data_or_acl")
        cls.password = "test-only-passphrase"
        cls.encoded = local_auth.hash_password(cls.password)

    @classmethod
    def migrate(cls, db, name):
        path = Path(__file__).resolve().parents[1] / "alembic/versions" / name
        spec = importlib.util.spec_from_file_location("isolated_test_revision", path)
        revision = importlib.util.module_from_spec(spec); spec.loader.exec_module(revision)
        with Operations.context(MigrationContext.configure(db)):
            revision.upgrade()

    @classmethod
    def tearDownClass(cls):
        for engine in (cls.owner, cls.writer, cls.reader):
            engine.dispose()

    def setUp(self):
        with self.owner.begin() as db:
            db.execute(text("DELETE FROM scm_auth.sessions"))
            db.execute(text("DELETE FROM scm_auth.login_limits"))
            db.execute(text("DELETE FROM scm_auth.credentials"))
            db.execute(text("DELETE FROM public.scm_user_grants"))
            db.execute(text("UPDATE public.users SET status='active'"))
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=true"))
            for uid in (1, 2):
                db.execute(text("INSERT INTO scm_auth.credentials VALUES (:id,:hash,true,:now)"),
                           {"id": uid, "hash": self.encoded, "now": int(time.time())})
                for kind, grant in (("action", "system.access"), ("action", "data.read"), ("menu", "/"), ("menu", "/sales")):
                    db.execute(text("INSERT INTO public.scm_user_grants (user_id,grant_type,grant_name,approved_by) VALUES (:id,:kind,:grant,1)"),
                               {"id": uid, "kind": kind, "grant": grant})
            db.execute(text("INSERT INTO public.scm_user_grants (user_id,grant_type,grant_name,approved_by) "
                            "VALUES (1,'action','admin.manage',1),(1,'menu','/settings/accounts',1)"))
        self.patcher = patch.object(local_auth, "engine", return_value=self.writer); self.patcher.start()
        self.origin = {"Origin": "http://127.0.0.1:8011"}
        self.settings = patch.object(auth_routes, "get_settings", return_value=SimpleNamespace(
            environment="development", frontend_origin="http://127.0.0.1:8011")); self.settings.start()
        self.environ = patch.dict(os.environ, {"SCM_FRONTEND_ORIGIN": "http://127.0.0.1:8011"}); self.environ.start()
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close(); self.patcher.stop(); self.settings.stop(); self.environ.stop()

    def sign_in(self, username="admin-local", password=None):
        return self.client.post("/api/v1/auth/login", headers=self.origin,
            json={"username": username, "password": password or self.password})

    def test_additive_migration_keeps_54_public_tables_users_and_mappings(self):
        with self.owner.connect() as db:
            self.assertEqual(db.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public'")).scalar_one(), 54)
            self.assertEqual(db.execute(text("SELECT * FROM public.users ORDER BY id")).all(), self.before_users)
            self.assertEqual(db.execute(text("SELECT * FROM public.scm_identity_mappings")).all(), self.before_mappings)
            self.assertEqual(db.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='scm_auth'")).scalar_one(), 3)

    def test_real_login_logout_and_persistent_hashed_session(self):
        with patch("httpx.Client", side_effect=AssertionError("external_auth_must_not_be_used")):
            self.assertEqual(self.sign_in().status_code, 200)
            token = self.client.cookies["scm_session"]
            self.writer.dispose()  # Simulates a fresh DB connection pool; session remains in DB.
            self.assertEqual(self.client.get("/api/v1/auth/me").json()["data"]["subject"], "1")
            with self.owner.connect() as db:
                stored = db.execute(text("SELECT token_hash FROM scm_auth.sessions")).scalar_one()
            self.assertEqual(stored, local_auth.digest(token)); self.assertNotEqual(stored, token)
            self.assertEqual(self.client.post("/api/v1/auth/logout", headers=self.origin).status_code, 200)
            self.assertIsNone(local_auth.lookup(token))
            self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)

    def test_incorrect_unknown_disabled_and_suspended_login_are_generic(self):
        self.assertEqual(self.sign_in(password="incorrect-test-password").json()["error"]["code"], "invalid_credentials")
        self.assertEqual(self.sign_in(username="unknown-local").json()["error"]["code"], "invalid_credentials")
        with self.owner.begin() as db:
            db.execute(text("UPDATE scm_auth.credentials SET enabled=false WHERE user_id=1"))
        self.assertEqual(self.sign_in().status_code, 401)
        with self.owner.begin() as db:
            db.execute(text("UPDATE scm_auth.credentials SET enabled=true WHERE user_id=1"))
            db.execute(text("UPDATE public.users SET status='suspended' WHERE id=1"))
        self.assertEqual(self.sign_in().status_code, 401)

    def test_expiry_and_user_or_grant_revocation_are_immediate(self):
        token = local_auth.login("employee-local", self.password, "test-peer")
        with self.owner.begin() as db:
            db.execute(text("UPDATE public.scm_identity_mappings SET is_active=false"))
        self.assertEqual(local_auth.lookup(token).subject, "2")
        with self.owner.begin() as db:
            db.execute(text("DELETE FROM public.scm_user_grants WHERE user_id=2 AND grant_name='system.access'"))
        self.assertNotIn("system.access", local_auth.lookup(token).action_grants)
        with self.owner.begin() as db:
            db.execute(text("UPDATE scm_auth.sessions SET expires_at=created_at+1"))
        with patch.object(local_auth.time, "time", return_value=time.time() + 1801):
            self.assertIsNone(local_auth.lookup(token))

    def test_admin_can_reset_existing_user_and_revoke_sessions_without_business_writes(self):
        old = local_auth.login("employee-local", self.password, "test-peer")
        self.assertEqual(self.sign_in().status_code, 200)
        response = self.client.get("/api/v1/admin/auth/users")
        self.assertEqual(response.status_code, 200); self.assertNotIn("password_hash", response.text)
        reset = self.client.post("/api/v1/admin/auth/users/2/credentials", headers=self.origin,
            json={"enabled": True, "password": "changed-test-passphrase"})
        self.assertEqual(reset.status_code, 200); self.assertIsNone(local_auth.lookup(old))
        self.assertEqual(local_auth.lookup(local_auth.login("employee-local", "changed-test-passphrase", "peer")).subject, "2")
        self.assertEqual(self.client.post("/api/v1/admin/auth/users/1/credentials", headers=self.origin,
                                         json={"enabled": False}).status_code, 409)
        with self.owner.connect() as db:
            self.assertEqual(db.execute(text("SELECT * FROM public.users ORDER BY id")).all(), self.before_users)

    def test_employee_cannot_call_admin_api_and_csrf_is_rejected(self):
        self.assertEqual(self.sign_in(username="employee-local").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/admin/auth/users").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/admin/auth/users/1/credentials", headers=self.origin,
                                         json={"enabled": False}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/logout", headers={"Origin": "https://other.example"}).status_code, 403)

    def test_login_attempts_are_atomic_across_concurrent_connections(self):
        def attempt(_):
            try:
                local_auth.login("admin-local", "incorrect-test-password", "test-peer")
            except local_auth.AuthFailure as exc:
                return exc.code
        with patch.object(local_auth, "hasher") as hasher:
            hasher.verify.return_value = False
            with ThreadPoolExecutor(max_workers=6) as executor:
                codes = list(executor.map(attempt, range(6)))
        self.assertEqual(codes.count("invalid_credentials"), 5)
        self.assertEqual(codes.count("login_rate_limited"), 1)
        with self.assertRaises(local_auth.AuthFailure) as failure:
            local_auth.login("admin-local", self.password, "different-peer")
        self.assertEqual(failure.exception.code, "login_rate_limited")

    def test_minimum_writer_rights_and_readonly_role_preserved(self):
        with self.writer.connect() as db:
            db.execute(text("SET TRANSACTION READ ONLY")); verify_auth_connection(db); db.rollback()
        for engine, sql in ((self.writer, "UPDATE public.users SET name='blocked' WHERE id=2"),
                            (self.writer, "SELECT password_hash FROM public.users"),
                            (self.writer, "DELETE FROM public.scm_identity_mappings"),
                            (self.writer, "CREATE TABLE public.unauthorized (id int)"),
                            (self.reader, "UPDATE public.users SET name='blocked' WHERE id=2"),
                            (self.reader, "DELETE FROM scm_auth.sessions")):
            with self.subTest(sql=sql), self.assertRaises(DBAPIError):
                with engine.begin() as db:
                    db.execute(text(sql))

    def test_disable_credentials_revokes_all_sessions(self):
        first = local_auth.login("employee-local", self.password, "test-peer")
        second = local_auth.login("employee-local", self.password, "test-peer")
        local_auth.set_credentials(2, None, False)
        self.assertIsNone(local_auth.lookup(first)); self.assertIsNone(local_auth.lookup(second))

    def test_blocked_peer_cannot_allocate_unbounded_account_buckets(self):
        now = int(time.time())
        with self.owner.begin() as db:
            db.execute(text("INSERT INTO scm_auth.login_limits VALUES (:key,:window,50,:expiry)"),
                {"key": "peer:" + local_auth.digest("blocked-test-peer"), "window": now // 900,
                 "expiry": (now // 900 + 2) * 900})
        for name in ("fake-first", "fake-second"):
            with self.assertRaises(local_auth.AuthFailure):
                local_auth._consume_attempt(name, "blocked-test-peer", now)
        with self.owner.connect() as db:
            self.assertEqual(db.execute(text("SELECT count(*) FROM scm_auth.login_limits")).scalar_one(), 1)

    def test_initial_admin_setup_is_interactive_and_preserves_existing_password_column(self):
        import contextlib
        import io
        from app.core import provision_auth
        with self.owner.begin() as db:
            db.execute(text("DELETE FROM scm_auth.credentials WHERE user_id=1"))
        with patch.object(provision_auth, "engine", return_value=self.writer), \
                patch.object(provision_auth.sys.stdin, "isatty", return_value=True), \
                patch.object(provision_auth, "getpass", side_effect=[self.password, self.password]) as prompt, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(provision_auth.main(["--user-id", "1", "--initial-admin"]), 0)
        self.assertEqual(prompt.call_count, 2)
        self.assertEqual(output.getvalue(), "PASS scm_credentials_provisioned_sessions_revoked\n")
        self.assertEqual(self.sign_in().status_code, 200)
        with self.owner.connect() as db:
            self.assertEqual(db.execute(text("SELECT password_hash FROM public.users WHERE id=1")).scalar_one(), "legacy-hash-preserved")
        with patch.object(provision_auth, "engine", return_value=self.writer), \
                patch.object(provision_auth.sys.stdin, "isatty", return_value=True), \
                patch.object(provision_auth, "getpass") as prompt, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(provision_auth.main(["--user-id", "2", "--initial-admin"]), 1)
        prompt.assert_not_called()

    def test_all_public_schema_data_acl_and_sequences_preserved_by_migration(self):
        self.assertEqual(len(self.public_before["tables"]), 54)
        self.assertEqual(sum(count for count, _digest in self.public_before["rows"].values()), 105)

    def test_auth_schema_catalog_drift_is_rejected(self):
        from app.db.auth_policy import verify_auth_schema
        cases = [("ALTER TABLE scm_auth.credentials ADD COLUMN unexpected integer", "auth_schema_columns_invalid"),
                 ("ALTER TABLE scm_auth.credentials ALTER COLUMN enabled SET DEFAULT true", "auth_schema_columns_invalid"),
                 ("ALTER TABLE scm_auth.login_limits DROP CONSTRAINT login_limits_pkey", "auth_schema_primary_keys_invalid"),
                 ("ALTER TABLE scm_auth.credentials DROP CONSTRAINT credentials_user_id_fkey", "auth_schema_foreign_keys_invalid"),
                 ("DROP INDEX scm_auth.ix_auth_sessions_expiry", "auth_schema_indexes_invalid"),
                 ("ALTER TABLE scm_auth.sessions DROP CONSTRAINT session_expiry", "auth_schema_checks_invalid"),
                 ("ALTER TABLE scm_auth.sessions DROP CONSTRAINT session_expiry, ADD CONSTRAINT session_expiry "
                  "CHECK (expires_at::text > created_at::text)", "auth_schema_checks_invalid")]
        for sql, code in cases:
            with self.subTest(code=code), self.owner.connect() as db:
                transaction = db.begin()
                try:
                    db.execute(text(sql))
                    with self.assertRaisesRegex(ValueError, "^" + code + "$"):
                        verify_auth_schema(db)
                finally:
                    transaction.rollback()

    def test_constraints_reject_invalid_hash_unknown_user_expiry_and_duplicate_session(self):
        token = local_auth.login("admin-local", self.password, "test-peer")
        cases = ["INSERT INTO scm_auth.credentials VALUES (999,'$argon2id$invalid',true,1)",
                 "UPDATE scm_auth.credentials SET password_hash='plaintext-is-forbidden' WHERE user_id=2",
                 "INSERT INTO scm_auth.sessions VALUES ('test-only-digest',999,1,2)",
                 "INSERT INTO scm_auth.sessions VALUES ('test-only-digest',1,2,1)"]
        for sql in cases:
            with self.subTest(sql=sql), self.assertRaises(DBAPIError):
                with self.owner.begin() as db:
                    db.execute(text(sql))
        with self.assertRaises(DBAPIError), self.owner.begin() as db:
            db.execute(text("INSERT INTO scm_auth.sessions VALUES (:hash,1,1,2)"), {"hash": local_auth.digest(token)})

    def test_post_migration_preflight_is_readonly_and_requires_explicit_admin_setup(self):
        import preflight
        reader_url = "postgresql+psycopg://new_scm_ro:test-only@localhost/new_scm_dev"
        writer_url = "postgresql+psycopg://new_scm_auth:test-only@localhost/new_scm_dev"
        readonly_writer = create_engine(self.writer.url, hide_parameters=True,
            connect_args={"options": "-c default_transaction_read_only=on"})
        try:
            with self.owner.connect() as db:
                before = fingerprint(db)
            with patch("sqlalchemy.create_engine", side_effect=[self.reader, readonly_writer]):
                preflight.runtime_checks(reader_url, writer_url)
            with self.owner.connect() as db:
                self.assertEqual(fingerprint(db), before)
            with self.owner.begin() as db:
                db.execute(text("UPDATE scm_auth.credentials SET enabled=false"))
            with patch("sqlalchemy.create_engine", side_effect=[self.reader, readonly_writer]), \
                    self.assertRaisesRegex(preflight.Pending, "^standalone_admin_setup_required$"):
                preflight.runtime_checks(reader_url, writer_url)
        finally:
            readonly_writer.dispose()

    @unittest.skipUnless(os.getenv("SCM_TEST_PG_CONTAINER"), "isolated local backup/restore fixture not supplied")
    def test_custom_backup_restores_pre_migration_schema_data_acl_and_sequences(self):
        recovered = restore(self.owner, self.before_archive)
        try:
            with recovered.connect() as db:
                self.assertEqual(fingerprint(db), self.before_snapshot)
                self.assertIsNone(db.execute(text("SELECT to_regnamespace('scm_auth')")).scalar_one())
                self.assertEqual(db.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one(), "20261027_0013")
        finally:
            recovered.dispose()

    @unittest.skipUnless(os.getenv("SCM_TEST_PG_CONTAINER"), "isolated local backup/restore fixture not supplied")
    def test_custom_backup_restores_post_migration_auth_and_business_data(self):
        local_auth.login("employee-local", self.password, "test-peer")
        with self.owner.connect() as db:
            before = fingerprint(db)
        recovered = restore(self.owner, backup())
        try:
            with recovered.connect() as db:
                self.assertEqual(fingerprint(db), before)
                self.assertEqual(db.execute(text("SELECT count(*) FROM scm_auth.sessions")).scalar_one(), 1)
        finally:
            recovered.dispose()

    @unittest.skipUnless(os.getenv("SCM_TEST_PG_CONTAINER"), "isolated local backup/restore fixture not supplied")
    def test_partial_ddl_failure_rolls_back_then_clean_retry_succeeds(self):
        recovered = restore(self.owner, self.before_archive)
        try:
            with self.assertRaisesRegex(RuntimeError, "fixture_injected_migration_failure"):
                with recovered.begin() as db, patch("alembic.op.create_index", side_effect=RuntimeError("fixture_injected_migration_failure")):
                    self.migrate(db, "20261028_0014_standalone_auth.py")
            with recovered.connect() as db:
                self.assertEqual(fingerprint(db), self.before_snapshot)
            with recovered.begin() as db:
                self.migrate(db, "20261028_0014_standalone_auth.py")
                db.execute(text("UPDATE public.alembic_version SET version_num='20261028_0014'"))
            with recovered.connect() as db:
                self.assertEqual(fingerprint(db, ignore_revision_data=True, include_auth=False, exclude_auth_role=True), self.public_before)
        finally:
            recovered.dispose()

    @unittest.skipUnless(os.getenv("SCM_TEST_PG_CONTAINER"), "isolated local backup/restore fixture not supplied")
    def test_unsafe_role_blocks_migration_before_schema_creation(self):
        recovered = restore(self.owner, self.before_archive)
        try:
            with recovered.begin() as db:
                db.execute(text("GRANT CREATE ON DATABASE " + db.dialect.identifier_preparer.quote(recovered.url.database) + " TO new_scm_auth"))
            with self.assertRaises(DBAPIError), recovered.begin() as db:
                self.migrate(db, "20261028_0014_standalone_auth.py")
            with recovered.connect() as db:
                self.assertIsNone(db.execute(text("SELECT to_regnamespace('scm_auth')")).scalar_one())
                self.assertEqual(db.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one(), "20261027_0013")
        finally:
            recovered.dispose()

    def test_schema_downgrade_is_blocked_without_data_loss(self):
        path = Path(__file__).resolve().parents[1] / "alembic/versions/20261028_0014_standalone_auth.py"
        spec = importlib.util.spec_from_file_location("test_standalone_downgrade", path)
        revision = importlib.util.module_from_spec(spec); spec.loader.exec_module(revision)
        with self.owner.connect() as db:
            before = fingerprint(db)
        with self.assertRaisesRegex(RuntimeError, "standalone_auth_downgrade_requires_reviewed_backup_restore"):
            revision.downgrade()
        with self.owner.connect() as db:
            self.assertEqual(fingerprint(db), before)


if __name__ == "__main__":
    unittest.main()
