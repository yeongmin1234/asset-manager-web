"""Fixed-output phase/protocol regressions; no NAS changes or probe writes."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import preflight
import protected_state
from test_preflight import config


def scalar(value):
    return SimpleNamespace(one=lambda: value, scalar_one=lambda: value,
                           scalars=lambda: SimpleNamespace(all=lambda: value))


class MigrationPhaseTests(unittest.TestCase):
    def test_pre_config_allows_unprovisioned_writer_but_post_remains_strict(self):
        candidate = config()
        candidate["services"]["backend"]["environment"]["SCM_AUTH_DATABASE_URL"] = ""
        preflight.validate_config(candidate, "pre-migration")
        with self.assertRaises(preflight.Rejected):
            preflight.validate_config(candidate)
        candidate["services"]["backend"]["environment"]["SCM_AUTH_DATABASE_URL"] = "private-test-invalid-url"
        with self.assertRaises(preflight.Rejected):
            preflight.validate_config(candidate, "pre-migration")

    def test_pre_db_checks_are_select_only_and_never_connect_future_writer(self):
        engine = MagicMock()
        db = engine.connect.return_value.__enter__.return_value
        db.execute.side_effect = [scalar(("new_scm_dev", "new_scm_ro", "on")), scalar(54),
            scalar(["20261027_0013"]), scalar(0), scalar(0), scalar(False), scalar(True)]
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        with patch("sqlalchemy.create_engine", return_value=engine) as factory, patch("httpx.Client") as http, \
                self.assertRaisesRegex(preflight.Pending, "^auth_migration_required$"):
            preflight.runtime_checks(url, phase="pre-migration")
        self.assertEqual(factory.call_count, 1)
        self.assertEqual(factory.call_args.args[0].username, "new_scm_ro")
        self.assertIn("default_transaction_read_only=on", factory.call_args.kwargs["connect_args"]["options"])
        self.assertTrue(all(str(call.args[0]).strip().startswith("SELECT ") for call in db.execute.call_args_list))
        http.assert_not_called(); db.rollback.assert_called_once(); engine.dispose.assert_called_once()

    def test_pre_migration_partial_schema_or_unsafe_readonly_role_is_fail(self):
        for writable, absent, expected in ((0, False, "pre_migration_revision_or_schema_invalid"),
                                           (1, True, "readonly_role_has_write_or_owner_privileges")):
            engine = MagicMock()
            db = engine.connect.return_value.__enter__.return_value
            db.execute.side_effect = [scalar(("new_scm_dev", "new_scm_ro", "on")), scalar(54),
                scalar(["20261027_0013"]), scalar(writable), scalar(0), scalar(False), scalar(absent)]
            url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
            with patch("sqlalchemy.create_engine", return_value=engine), \
                    self.assertRaisesRegex(preflight.Rejected, "^" + expected + "$") as raised:
                preflight.runtime_checks(url, phase="pre-migration")
            self.assertIs(type(raised.exception), preflight.Rejected)

    def test_pending_worker_protocol_has_distinct_reserved_exit(self):
        for code in preflight.PENDING_CODES:
            stdout = (preflight.WORKER_STARTED + "\nPENDING " + code + "\n").encode()
            result = subprocess.CompletedProcess([], preflight.WORKER_PENDING_EXIT, stdout=stdout)
            self.assertEqual(preflight.verifier_result_code(result), code)
            result.returncode = 0
            self.assertEqual(preflight.verifier_result_code(result), "verifier_result_invalid")
        result = subprocess.CompletedProcess([], preflight.WORKER_PENDING_EXIT,
            stdout=(preflight.WORKER_STARTED + "\nPENDING private-test-value\n").encode())
        self.assertEqual(preflight.verifier_result_code(result), "verifier_result_invalid")

    def test_worker_pre_phase_and_legacy_post_payloads_use_fixed_pending_output(self):
        base = {"script_sha256": preflight.script_digest(), "database_url": "test-only-reader", "auth_database_url": ""}
        for phase, code in (("pre-migration", "auth_migration_required"), ("post-migration", "standalone_admin_setup_required")):
            payload = dict(base)
            if phase == "pre-migration":
                payload["phase"] = phase
            with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                    patch.object(preflight, "runtime_checks", side_effect=preflight.Pending(code)) as runtime, \
                    contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(preflight.isolated_worker(), preflight.WORKER_PENDING_EXIT)
            self.assertEqual(out.getvalue(), "PENDING " + code + "\n")
            if phase == "pre-migration":
                runtime.assert_called_once_with("test-only-reader", "", phase=phase)
            else:
                runtime.assert_called_once_with("test-only-reader", "")

    def test_invalid_phase_and_unregistered_pending_cannot_echo_values(self):
        payload = {"script_sha256": preflight.script_digest(), "database_url": "test-only-reader",
                   "auth_database_url": "", "phase": "private-test-value"}
        with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(preflight.isolated_worker(), preflight.WORKER_POLICY_EXIT)
        self.assertEqual(out.getvalue(), "FAIL migration_phase_invalid\n")
        payload.pop("phase")
        with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                patch.object(preflight, "runtime_checks", side_effect=preflight.Pending("private-test-value")), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(preflight.isolated_worker(), preflight.WORKER_POLICY_EXIT)
        self.assertEqual(out.getvalue(), "FAIL verifier_unregistered_failure\n")

    def test_protected_state_change_overrides_expected_pending(self):
        with patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "protected_state", side_effect=[b"before", b"after"]), \
                patch.object(preflight, "host_docker_checks"), \
                patch.object(preflight, "runtime_checks", side_effect=preflight.Pending("auth_migration_required")), \
                self.assertRaisesRegex(preflight.Rejected, "^protected_listeners_or_postgres_state_changed$") as raised:
            preflight.host_checks({"SCM_AUTH_DATABASE_URL": ""}, "test-only-reader", phase="pre-migration")
        self.assertIs(type(raised.exception), preflight.Rejected)

    def test_cli_pending_returns_two_and_does_not_report_deployment_success(self):
        candidate = config(); candidate["services"]["backend"]["environment"]["SCM_AUTH_DATABASE_URL"] = ""
        with patch.object(sys, "argv", ["preflight.py", "--phase", "pre-migration"]), \
                patch.object(preflight, "compose_config", return_value=candidate), \
                patch.object(preflight, "host_checks", side_effect=preflight.Pending("auth_migration_required")), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(preflight.main(), 2)
        self.assertIn("PENDING auth_migration_required", out.getvalue())
        self.assertNotIn(candidate["services"]["backend"]["environment"]["SCM_DATABASE_URL"], out.getvalue())

    def test_config_only_pre_phase_never_calls_host_or_db(self):
        candidate = config(); candidate["services"]["backend"]["environment"]["SCM_AUTH_DATABASE_URL"] = ""
        with patch.object(sys, "argv", ["preflight.py", "--phase", "pre-migration", "--config-only"]), \
                patch.object(preflight, "compose_config", return_value=candidate), \
                patch.object(preflight, "host_checks") as host, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(preflight.main(), 0)
        host.assert_not_called()
        self.assertIn("PENDING database_runtime_checks_not_run", out.getvalue())

    def test_invalid_cli_arguments_are_fixed_and_private(self):
        with patch.object(sys, "argv", ["preflight.py", "--phase", "private-test-value"]), \
                contextlib.redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as raised:
            preflight.main()
        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(out.getvalue(), "FAIL arguments_invalid\n")

    def test_isolated_pending_keeps_credentials_off_arguments_and_mounts(self):
        code = "auth_migration_required"
        result = subprocess.CompletedProcess([], preflight.WORKER_PENDING_EXIT,
            stdout=(preflight.WORKER_STARTED + "\nPENDING " + code + "\n").encode())
        with patch.object(preflight, "verifier_resource_limits", return_value=(False, False)), \
                patch.object(preflight, "docker_command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", return_value=result) as run, \
                self.assertRaisesRegex(preflight.Pending, "^auth_migration_required$"):
            preflight.isolated_runtime_checks("test-only-reader-private", "test-image", phase="pre-migration")
        self.assertNotIn("test-only-reader-private", " ".join(run.call_args.args[0]))
        self.assertNotIn("--mount", run.call_args.args[0])
        self.assertEqual(json.loads(run.call_args.kwargs["input"])["phase"], "pre-migration")

    @unittest.skipUnless(os.getenv("SCM_TEST_COMPOSE"), "standalone Compose not supplied")
    def test_real_compose_pre_phase_and_test_profile_allow_blank_future_writer(self):
        with tempfile.TemporaryDirectory(prefix="scm-pre-phase-") as directory:
            env_file, images = Path(directory) / ".env", Path(directory) / ".images.env"
            values = config()["services"]["backend"]["environment"].copy()
            values.pop("SCM_DATABASE_SOCKET_DIR"); values["SCM_AUTH_DATABASE_URL"] = ""
            env_file.write_text("\n".join(key + "=" + value for key, value in values.items()) + "\n")
            env_file.chmod(0o600)
            images.write_text("SCM_TEST_BACKEND_IMAGE=sha256:" + "a" * 64 + "\nSCM_TEST_FRONTEND_IMAGE=sha256:" + "b" * 64 + "\n")
            images.chmod(0o600)
            resolved = preflight.compose_config(os.environ["SCM_TEST_COMPOSE"], env_file)
            preflight.validate_config(resolved, "pre-migration")
            protected_state.verify_test_config(env_file, images, os.environ["SCM_TEST_COMPOSE"], phase="pre-migration")
