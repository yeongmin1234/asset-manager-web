import contextlib
import ast
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import preflight
import protected_state
from app.core import nas_check


class NasPreparationTests(unittest.TestCase):
    @unittest.skipUnless(os.getenv("SCM_TEST_COMPOSE"), "standalone Compose not supplied")
    def test_local_test_compose_isolates_images_ports_users_and_resources(self):
        from test_preflight import config
        with tempfile.TemporaryDirectory(prefix="scm-test-profile-") as directory:
            env_file, images = Path(directory) / ".env", Path(directory) / ".images.env"
            values = config()["services"]["backend"]["environment"].copy()
            values.pop("SCM_DATABASE_SOCKET_DIR")
            env_file.write_text("\n".join(key + "=" + value for key, value in values.items()) + "\n", encoding="utf-8")
            env_file.chmod(0o600)
            backend, frontend = "sha256:" + "a" * 64, "sha256:" + "b" * 64
            images.write_text("SCM_TEST_BACKEND_IMAGE=" + backend + "\nSCM_TEST_FRONTEND_IMAGE=" + frontend + "\n")
            images.chmod(0o600)
            protected_state.verify_test_config(env_file, images, os.environ["SCM_TEST_COMPOSE"])
            environment = {k: v for k, v in os.environ.items() if not k.startswith(("SCM_", "COMPOSE_", "VITE_"))}
            environment["SCM_ENV_FILE"] = str(env_file)
            result = subprocess.run([os.environ["SCM_TEST_COMPOSE"], "--project-name", "new-scm-4-2h",
                                     "--env-file", str(env_file), "--env-file", str(images),
                                     "-f", str(preflight.ROOT / "deploy/compose.nas-test.yaml"),
                                     "config", "--format", "json"], env=environment, capture_output=True)
            self.assertEqual(result.returncode, 0, "test_profile_invalid_output_suppressed")
            resolved = json.loads(result.stdout)
        self.assertEqual(resolved["name"], "new-scm-4-2h")
        services = resolved["services"]
        self.assertEqual(set(services), {"frontend", "backend", "db-relay"})
        for name, memory, uid in (("db-relay", 64, "10001:10001"), ("backend", 256, "10001:10001"),
                                  ("frontend", 128, "101:101")):
            service = services[name]
            self.assertTrue(service["read_only"])
            self.assertEqual(service["user"], uid)
            self.assertEqual(int(service["mem_limit"]), memory * 1024 * 1024)
            self.assertEqual(service["pull_policy"], "never")
            self.assertEqual(service["restart"], "no")
            self.assertEqual(service["logging"]["driver"], "none")
            self.assertIn("ALL", service["cap_drop"])
            self.assertIn("no-new-privileges:true", service["security_opt"])
            for field in ("build", "privileged", "container_name", "cpus", "pids_limit"):
                self.assertFalse(service.get(field))
            self.assertEqual(service["image"], frontend if name == "frontend" else backend)
        self.assertEqual(services["db-relay"]["network_mode"], "host")
        self.assertFalse(services["db-relay"].get("ports"))
        self.assertFalse(services["backend"].get("ports"))
        self.assertFalse(services["frontend"].get("environment"))
        ports = services["frontend"]["ports"]
        self.assertEqual(len(ports), 1)
        self.assertEqual((ports[0]["host_ip"], str(ports[0]["published"]), ports[0]["target"]),
                         ("127.0.0.1", "8011", 8081))
        for name, readonly in (("db-relay", False), ("backend", True)):
            mount = services[name]["volumes"]
            self.assertEqual(len(mount), 1)
            self.assertEqual((mount[0]["type"], mount[0]["source"], mount[0]["target"]),
                             ("volume", "scm_db_socket", "/srv/new-scm/db-socket"))
            self.assertEqual(mount[0].get("read_only", False), readonly)
        self.assertFalse(services["frontend"].get("volumes"))
        self.assertEqual(resolved["volumes"]["scm_db_socket"]["name"], "new-scm-4-2h_scm_db_socket")
        self.assertFalse(resolved["volumes"]["scm_db_socket"].get("external"))
        self.assertEqual(resolved["networks"]["scm_internal"]["name"], "new-scm-4-2h_scm_internal")

    def test_image_file_cannot_override_runtime_settings_or_duplicate_ids(self):
        with tempfile.TemporaryDirectory(prefix="scm-images-policy-") as directory:
            images = Path(directory) / ".images.env"
            prefix = "SCM_TEST_BACKEND_IMAGE=sha256:" + "a" * 64 + "\nSCM_TEST_FRONTEND_IMAGE=sha256:" + "b" * 64 + "\n"
            for suffix in ("SCM_BIND_HOST=0.0.0.0\n", "SCM_TEST_BACKEND_IMAGE=sha256:" + "c" * 64 + "\n"):
                images.write_text(prefix + suffix)
                images.chmod(0o600)
                with patch.object(preflight, "compose_config") as compose, \
                        self.assertRaisesRegex(preflight.Rejected, "^nas_test_image_file_invalid$"):
                    protected_state.verify_test_config(image_file=images)
                compose.assert_not_called()

    def test_snapshot_tool_rejects_mutating_docker_queries(self):
        ast.parse(Path(protected_state.__file__).read_text(encoding="utf-8"), feature_version=(3, 8))
        with patch.object(preflight, "command") as command, \
                self.assertRaisesRegex(preflight.Rejected, "^protected_query_not_allowed$"):
            protected_state.docker_read(["restart", "asset-postgres"], True)
        command.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX ownership required")
    def test_snapshot_uses_only_hashes_and_warns_for_older_docker(self):
        with tempfile.TemporaryDirectory(prefix="scm-protected-") as directory:
            root = Path(directory)
            (root / ".env").write_text("SCM_HANDOFF_KEY=test-only-private\n")
            (root / ".env").chmod(0o600)
            (root / ".nas-test-images.env").write_text("test-image-fixture")
            (root / ".nas-test-images.env").chmod(0o600)
            (root / "deploy").mkdir()
            (root / "deploy/compose.nas-test.yaml").write_text("test-profile-fixture")
            def docker(args, _sudo):
                if args[0] == "inspect":
                    return json.dumps({"running": True, "paused": False, "restarting": False, "oom": False})
                return "27.0.0" if args[0] == "info" else ""
            output = io.StringIO()
            with patch.object(protected_state, "ROOT", root), patch.object(protected_state.sys, "platform", "linux"), \
                    patch.object(preflight.shutil, "which", return_value="/usr/bin/ss"), \
                    patch.object(preflight, "command", return_value="127.0.0.1:3010 peer\n127.0.0.1:8010 peer\n127.0.0.1:15432 peer"), \
                    patch.object(protected_state, "docker_read", side_effect=docker), \
                    patch.object(protected_state, "http_status", return_value=200), contextlib.redirect_stdout(output):
                state = protected_state.collect(require_free_port=True)
            self.assertNotIn("test-only-private", json.dumps(state))
            self.assertEqual(output.getvalue(), "WARN docker_loopback_l2_protection_unverified\n")
        self.assertEqual(state["http"], [])

    @unittest.skipUnless(os.name == "posix", "POSIX ownership required")
    def test_capture_compare_and_no_overwrite_of_protected_baseline(self):
        with tempfile.TemporaryDirectory(prefix="scm-manifest-") as directory:
            root = Path(directory)
            with patch.object(protected_state, "ROOT", root), \
                    patch.object(protected_state, "collect", return_value={"schema": 1, "env": "synthetic-fingerprint"}), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(protected_state.main(["capture"]), 0)
                self.assertEqual(protected_state.main(["capture"]), 1)
                self.assertEqual(protected_state.main(["compare"]), 0)
            target = root / "runtime/4-2h/protected-before.json"
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            with patch.object(protected_state, "ROOT", root), \
                    patch.object(protected_state, "collect", return_value={"schema": 1, "env": "changed"}), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(protected_state.main(["compare"]), 1)
            self.assertEqual(output.getvalue(), "FAIL protected_state_changed\n")

    def test_snapshot_path_cannot_escape_new_scm(self):
        with tempfile.TemporaryDirectory(prefix="scm-manifest-path-") as directory:
            with patch.object(protected_state, "ROOT", Path(directory)), \
                    self.assertRaisesRegex(preflight.Rejected, "^protected_snapshot_path_invalid$"):
                protected_state.snapshot_path("../outside.json")

    def test_runtime_probes_emit_no_exception_details(self):
        for name in ("socket", "database", "auth", "health"):
            output = io.StringIO()
            with self.subTest(name=name), patch.object(nas_check, "check_" + name,
                      side_effect=RuntimeError("test-only-private")), contextlib.redirect_stdout(output):
                self.assertEqual(nas_check.main([name]), 1)
            self.assertEqual(output.getvalue(), "FAIL nas_test_" + name + "\n")

    def test_host_http_probe_needs_all_three_endpoints_without_docker_access(self):
        for flags, expected in (([True, True], 0), ([False, True], 1)):
            output = io.StringIO()
            with patch.object(protected_state, "http_status", return_value=200), \
                    patch.object(protected_state, "scm_json_ok", side_effect=flags), \
                    patch.object(protected_state, "docker_read") as docker, contextlib.redirect_stdout(output):
                self.assertEqual(protected_state.main(["check-http"]), expected)
            docker.assert_not_called()
            self.assertNotIn("503", output.getvalue())

    def test_scm_http_validation_rejects_spa_html_and_other_services(self):
        for body, expected in ((b'{"ok":true,"data":{"service":"new-scm"}}', True),
                               (b'{"ok":true,"data":{"service":"other"}}', False),
                               (b'<html>test-only-private</html>', None)):
            opener, response = MagicMock(), MagicMock(status=200)
            opener.open.return_value.__enter__.return_value = response
            response.read.return_value = body
            with patch.object(protected_state.urllib.request, "build_opener", return_value=opener):
                if expected is None:
                    with self.assertRaises(ValueError):
                        protected_state.scm_json_ok("http://127.0.0.1:8011/health")
                else:
                    self.assertEqual(protected_state.scm_json_ok("http://127.0.0.1:8011/health"), expected)
            response.read.assert_called_once_with(65536)

    def test_backend_auth_probe_is_read_only_and_never_calls_asset_api(self):
        engine = MagicMock()
        with patch("app.db.local_auth.engine", return_value=engine), \
                patch("app.db.auth_policy.verify_auth_connection") as policy, patch("httpx.Client") as http:
            nas_check.check_auth()
        db = engine.connect.return_value.__enter__.return_value
        self.assertEqual(str(db.execute.call_args.args[0]), "SET TRANSACTION READ ONLY")
        db.rollback.assert_called_once()
        policy.assert_called_once_with(db)
        http.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX socket ownership required")
    def test_socket_probe_checks_owners_and_mode_before_connecting(self):
        from app.db import relay
        for mode in (0o700, 0o777):
            directory = SimpleNamespace(st_uid=10001, st_gid=10001, st_mode=0o40700)
            endpoint = SimpleNamespace(st_uid=10001, st_gid=10001, st_mode=stat.S_IFSOCK | mode)
            with self.subTest(mode=mode), patch.object(nas_check.os, "geteuid", return_value=10001), \
                    patch.object(nas_check.os, "getegid", return_value=10001), \
                    patch.object(nas_check.Path, "stat", side_effect=[directory, endpoint]), \
                    patch.object(relay, "check") as connect:
                if mode == 0o700:
                    nas_check.check_socket()
                    connect.assert_called_once()
                else:
                    with self.assertRaises(ValueError):
                        nas_check.check_socket()
                    connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
