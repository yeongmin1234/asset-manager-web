import copy
import ast
import contextlib
import io
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("scm_preflight", Path(__file__).with_name("preflight.py"))
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


def config():
    return {"services": {
        "db-relay": {"network_mode": "host", "read_only": True},
        "frontend": {"networks": {"scm_internal": {}},
                     "ports": [{"host_ip": "127.0.0.1", "published": "8011", "target": 80}],
                     "build": {"args": {"VITE_SCM_API_BASE_URL": "/api/v1"}}},
        "backend": {"networks": {"scm_internal": {}}, "extra_hosts": {"nas-host": "172.17.0.1"},
                    "environment": {
                        "SCM_ENV": "development",
                        "SCM_DATABASE_URL": "postgresql+psycopg://new_scm_ro:test-only@localhost:15432/new_scm_dev",
                        "SCM_DATABASE_SOCKET_DIR": "/srv/new-scm/db-socket",
                        "SCM_DIAGNOSTICS_KEY": "test-diagnostics-" * 3, "SCM_CORS_ORIGINS": "",
                        "SCM_BIND_HOST": "127.0.0.1", "SCM_HTTP_PORT": "8011",
                        "VITE_SCM_API_BASE_URL": "/api/v1", "SCM_IDENTITY_BASE_URL": "http://nas-host:8010",
                        "SCM_HANDOFF_KEY": "test-handoff-" * 4,
                        "SCM_HANDOFF_ORIGIN": "http://127.0.0.1:3010",
                        "SCM_FRONTEND_ORIGIN": "http://127.0.0.1:8011"}},
    }}


def worker_output(line="PASS isolated_db_api_checks"):
    return (preflight.WORKER_STARTED + "\n" + line + "\n").encode()


class PreflightTests(unittest.TestCase):
    def test_result_protocol_distinguishes_docker_python_and_probe_failures(self):
        cases = [(125, b"private", "docker_run_failed"),
                 (126, b"private", "verifier_command_not_executable"),
                 (127, b"private", "verifier_command_not_found"),
                 (137, b"private", "isolated_process_killed"),
                 (130, b"", "isolated_process_interrupted"),
                 (143, b"", "isolated_process_terminated"),
                 (-9, b"", "docker_cli_interrupted"),
                 (0, worker_output(), None),
                 (preflight.WORKER_EXCEPTION_EXIT, worker_output("FAIL verifier_python_exception"), "verifier_python_exception"),
                 (preflight.WORKER_BOOTSTRAP_EXIT, worker_output("FAIL verifier_python_bootstrap_failed"), "verifier_python_bootstrap_failed")]
        for exit_code, stdout, expected in cases:
            with self.subTest(exit_code=exit_code):
                result = subprocess.CompletedProcess([], exit_code, stdout=stdout, stderr=b"test-only-private")
                self.assertEqual(preflight.verifier_result_code(result), expected)
        for code in preflight.WORKER_POLICY_CODES:
            result = subprocess.CompletedProcess([], preflight.WORKER_POLICY_EXIT, stdout=worker_output("FAIL " + code))
            self.assertEqual(preflight.verifier_result_code(result), code)

    def test_missing_malformed_and_conflicting_worker_results_are_never_echoed(self):
        cases = [(0, b"", "verifier_result_missing"),
                 (1, b"test-only-private", "verifier_start_unconfirmed"),
                 (1, (preflight.WORKER_STARTED + "\n").encode(), "verifier_python_process_failed"),
                 (0, worker_output("FAIL expected_54_tables"), "verifier_result_invalid"),
                 (1, worker_output("FAIL expected_54_tables"), "verifier_result_invalid"),
                 (20, worker_output("FAIL test-only-private"), "verifier_result_invalid"),
                 (0, worker_output() + b"test-only-private\n", "verifier_result_invalid"),
                 (21, b"\xff", "verifier_result_invalid")]
        for exit_code, stdout, expected in cases:
            with self.subTest(exit_code=exit_code, expected=expected):
                result = subprocess.CompletedProcess([], exit_code, stdout=stdout, stderr=b"private")
                self.assertEqual(preflight.verifier_result_code(result), expected)

    def test_python_bootstrap_catches_script_load_errors_without_tracebacks(self):
        with tempfile.TemporaryDirectory(prefix="scm-bootstrap-") as directory:
            path = Path(directory) / "worker.py"
            bootstrap = preflight.WORKER_BOOTSTRAP.replace("'/srv/new-scm/deploy/preflight.py'", repr(str(path)))
            for source in (None, "def broken(:\n test_only_private", "raise RuntimeError('test-only-private')"):
                if source is not None:
                    path.write_text(source, encoding="utf-8")
                result = subprocess.run([sys.executable, "-I", "-B", "-c", bootstrap], capture_output=True)
                self.assertEqual(result.returncode, preflight.WORKER_BOOTSTRAP_EXIT)
                self.assertEqual(preflight.verifier_result_code(result), "verifier_python_bootstrap_failed")
                self.assertNotIn(b"test-only-private", result.stdout + result.stderr)
                self.assertNotIn(b"Traceback", result.stderr)

    def test_real_python_worker_exception_uses_reserved_exit_and_registered_protocol(self):
        with tempfile.TemporaryDirectory(prefix="scm-worker-protocol-") as directory:
            path = Path(directory) / "worker.py"
            path.write_text("import runpy\nmodule=runpy.run_path(" + repr(preflight.__file__) + ")\n"
                            "def fail(_): raise TypeError('test-only-private')\n"
                            "module['isolated_worker'].__globals__['runtime_checks']=fail\n"
                            "raise SystemExit(module['isolated_worker']())\n", encoding="utf-8")
            bootstrap = preflight.WORKER_BOOTSTRAP.replace("'/srv/new-scm/deploy/preflight.py'", repr(str(path)))
            payload = {"script_sha256": preflight.script_digest(), "database_url": "test-only-url"}
            result = subprocess.run([sys.executable, "-I", "-B", "-c", bootstrap],
                                    input=json.dumps(payload).encode(), capture_output=True)
            self.assertEqual(result.returncode, preflight.WORKER_EXCEPTION_EXIT)
            self.assertEqual(preflight.verifier_result_code(result), "verifier_python_exception")
            self.assertNotIn(b"test-only-private", result.stdout + result.stderr)

    def test_worker_input_and_unregistered_rejections_cannot_expose_values(self):
        for raw in ("invalid-json", "[]", json.dumps({"database_url": "test-only-private"})):
            output = io.StringIO()
            with patch.object(sys, "stdin", io.StringIO(raw)), patch.object(preflight, "runtime_checks") as runtime, \
                    contextlib.redirect_stdout(output):
                self.assertEqual(preflight.isolated_worker(), preflight.WORKER_POLICY_EXIT)
            runtime.assert_not_called()
            self.assertEqual(output.getvalue(), "FAIL verifier_input_invalid\n")
        output = io.StringIO()
        payload = {"script_sha256": preflight.script_digest(), "database_url": "test-only-url"}
        with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                patch.object(preflight, "runtime_checks", side_effect=preflight.Rejected("test-only-private")), \
                contextlib.redirect_stdout(output):
            self.assertEqual(preflight.isolated_worker(), preflight.WORKER_POLICY_EXIT)
        self.assertEqual(output.getvalue(), "FAIL verifier_unregistered_failure\n")

    def test_cli_execution_errors_have_fixed_codes_even_when_cleanup_also_fails(self):
        cases = [(FileNotFoundError("test-only-private"), "docker_cli_executable_missing"),
                 (PermissionError("test-only-private"), "docker_cli_execution_failed"),
                 (subprocess.TimeoutExpired("test-only-private", 90), "docker_cli_timeout")]
        for error, expected in cases:
            output = io.StringIO()
            with self.subTest(expected=expected), \
                    patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                    patch.object(preflight, "docker_command", return_value="sha256:" + "a" * 64), \
                    patch.object(preflight.subprocess, "run", side_effect=[error, subprocess.CompletedProcess([], 1)]) as run, \
                    contextlib.redirect_stdout(output), self.assertRaisesRegex(preflight.Rejected, "^" + expected + "$"):
                preflight.isolated_runtime_checks("test-only-url", "local-verifier")
            self.assertEqual(output.getvalue(), "WARN isolated_verifier_cleanup_failed\n")
            self.assertEqual(run.call_count, 2)

    def test_docker_run_failure_is_not_masked_by_failed_cleanup(self):
        output = io.StringIO()
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight, "docker_command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", side_effect=[subprocess.CompletedProcess([], 125, stdout=b"private"),
                                                                      subprocess.CompletedProcess([], 1)]), \
                contextlib.redirect_stdout(output), self.assertRaisesRegex(preflight.Rejected, "^docker_run_failed$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")
        self.assertEqual(output.getvalue(), "WARN isolated_verifier_cleanup_failed\n")

    def test_database_driver_errors_are_classified_by_phase(self):
        from sqlalchemy.exc import ArgumentError, OperationalError
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        for phase, expected in (("configuration", "database_configuration_invalid"),
                                ("connection", "database_connection_failed"), ("query", "database_query_failed")):
            engine = MagicMock()
            error = OperationalError(None, None, RuntimeError("test-only-private"))
            if phase == "connection":
                engine.connect.side_effect = error
            if phase == "query":
                engine.connect.return_value.__enter__.return_value.execute.side_effect = error
            kwargs = {"side_effect": ArgumentError("test-only-private")} if phase == "configuration" else {"return_value": engine}
            with self.subTest(phase=phase), patch("sqlalchemy.create_engine", **kwargs), \
                    patch.object(preflight, "identity_api_checks") as api, \
                    self.assertRaisesRegex(preflight.Rejected, "^" + expected + "$"):
                preflight.runtime_checks(url)
            api.assert_not_called()

    def test_database_cleanup_error_does_not_corrupt_original_worker_protocol(self):
        from sqlalchemy.exc import OperationalError
        engine = MagicMock()
        engine.connect.side_effect = OperationalError(None, None, RuntimeError("test-only-private-connect"))
        engine.dispose.side_effect = OperationalError(None, None, RuntimeError("test-only-private-cleanup"))
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        output = io.StringIO()
        with patch("sqlalchemy.create_engine", return_value=engine), contextlib.redirect_stdout(output), \
                self.assertRaisesRegex(preflight.Rejected, "^database_connection_failed$"):
            preflight.runtime_checks(url)
        self.assertEqual(output.getvalue(), "")

    def test_api_transport_status_and_response_failures_are_distinct(self):
        import httpx
        for failure, expected in (("connect", "identity_api_connection_failed"), ("status", "identity_openapi_unreachable"),
                                  ("json", "identity_api_response_invalid"), ("shape", "identity_api_response_invalid"),
                                  ("routes", "running_identity_handoff_routes_missing")):
            response = MagicMock(status_code=503 if failure == "status" else 200)
            response.json.return_value = [] if failure == "shape" else {"paths": {}}
            if failure == "json":
                response.json.side_effect = ValueError("test-only-private")
            with self.subTest(failure=failure), patch("httpx.Client") as http, \
                    self.assertRaisesRegex(preflight.Rejected, "^" + expected + "$"):
                client = http.return_value.__enter__.return_value
                if failure == "connect":
                    client.get.side_effect = httpx.ConnectError("test-only-private")
                else:
                    client.get.return_value = response
                preflight.identity_api_checks()
            client.post.assert_not_called()

    def test_original_verifier_failure_survives_failed_host_state_recheck(self):
        output = io.StringIO()
        with patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "protected_state", side_effect=[b"before", preflight.Rejected("docker_sudo_command_failed")]), \
                patch.object(preflight, "host_docker_checks"), \
                patch.object(preflight, "isolated_runtime_checks", side_effect=preflight.Rejected("database_connection_failed")), \
                contextlib.redirect_stdout(output), self.assertRaisesRegex(preflight.Rejected, "^database_connection_failed$"):
            preflight.host_checks({}, "test-only-url", "local-verifier")
        self.assertEqual(output.getvalue(), "WARN protected_state_recheck_failed\n")

    def test_resource_capabilities_choose_only_supported_limits_with_or_without_sudo(self):
        for sudo in (False, True):
            for period in (False, True):
                for quota in (False, True):
                    for pids in (False, True):
                        capabilities = {"cpu_period": period, "cpu_quota": quota, "pids": pids, "memory": True}
                        output = io.StringIO()
                        result = subprocess.CompletedProcess([], 0, stdout=worker_output(), stderr=b"")
                        with self.subTest(sudo=sudo, capabilities=capabilities), \
                                patch.object(preflight.sys, "platform", "linux"), \
                                patch.object(preflight, "trusted_executable", side_effect=lambda name: "/usr/bin/" + name), \
                                patch.object(preflight, "docker_command", side_effect=[json.dumps(capabilities), "sha256:" + "a" * 64]) as query, \
                                patch.object(preflight.subprocess, "run", return_value=result) as run, \
                                contextlib.redirect_stdout(output):
                            preflight.isolated_runtime_checks("test-only-url", "local-verifier", sudo)
                        self.assertEqual(query.call_args_list[0].args, (preflight.DOCKER_RESOURCE_INFO_ARGS, sudo))
                        args = run.call_args.args[0]
                        self.assertEqual("--cpus=1" in args, period and quota)
                        self.assertEqual("--pids-limit=64" in args, pids)
                        for option in ("--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
                                       "--user=10001:10001", "--memory=256m", "--tmpfs=/tmp:rw,noexec,nosuid,size=16m"):
                            self.assertIn(option, args)
                        expected = []
                        if not (period and quota):
                            expected.append("WARN verifier_cpu_limit_unsupported")
                        if not pids:
                            expected.append("WARN verifier_pid_limit_unsupported")
                        if expected:
                            expected.append("WARN verifier_resource_limits_incomplete")
                        self.assertEqual(output.getvalue().splitlines(), expected)
                        run.assert_called_once()

    def test_unknown_resource_capabilities_stop_without_container_or_raw_output(self):
        values = ["test-only-private", "null", "[]", "{}",
                  json.dumps({"cpu_period": True, "cpu_quota": True, "pids": True}),
                  json.dumps({"cpu_period": None, "cpu_quota": True, "pids": True, "memory": True}),
                  json.dumps({"cpu_period": "true", "cpu_quota": True, "pids": True, "memory": True}),
                  json.dumps({"cpu_period": True, "cpu_quota": True, "pids": 1, "memory": True}),
                  json.dumps({"cpu_period": True, "cpu_quota": True, "pids": True, "memory": True, "extra": True})]
        for value in values:
            output = io.StringIO()
            with self.subTest(case=values.index(value)), patch.object(preflight, "docker_command", return_value=value) as query, \
                    patch.object(preflight.subprocess, "run") as run, contextlib.redirect_stdout(output), \
                    self.assertRaisesRegex(preflight.Rejected, "^verifier_resource_capabilities_invalid$"):
                preflight.isolated_runtime_checks("test-only-url", "local-verifier")
            self.assertEqual(output.getvalue(), "")
            query.assert_called_once_with(preflight.DOCKER_RESOURCE_INFO_ARGS, False)
            run.assert_not_called()

    def test_memory_support_is_mandatory_and_never_dropped(self):
        capabilities = {"cpu_period": False, "cpu_quota": False, "pids": False, "memory": False}
        with patch.object(preflight, "docker_command", return_value=json.dumps(capabilities)), \
                patch.object(preflight.subprocess, "run") as run, \
                self.assertRaisesRegex(preflight.Rejected, "^verifier_memory_limit_unsupported$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")
        run.assert_not_called()

    def test_capability_query_failure_does_not_guess_or_start_a_verifier(self):
        for sudo in (False, True):
            code = "docker_sudo_command_failed" if sudo else "docker_command_failed"
            with self.subTest(sudo=sudo), patch.object(preflight, "docker_command", side_effect=preflight.Rejected(code)), \
                    patch.object(preflight.subprocess, "run") as run, \
                    self.assertRaisesRegex(preflight.Rejected, "^" + code + "$"):
                preflight.isolated_runtime_checks("test-only-url", "local-verifier", sudo)
            run.assert_not_called()

    def test_optional_resource_limits_do_not_relax_mandatory_security_allowlist(self):
        name, image = "scm-preflight-" + "b" * 32, "sha256:" + "a" * 64
        for cpu, pids in ((True, True), (True, False), (False, True), (False, False)):
            args = preflight.verifier_run_args(name, image, cpu, pids)
            preflight.docker_argv(args, False, cpu, pids)
            for mandatory in ("--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
                              "--user=10001:10001", "--memory=256m", "--tmpfs=/tmp:rw,noexec,nosuid,size=16m"):
                with self.subTest(cpu=cpu, pids=pids, mandatory=mandatory), self.assertRaises(preflight.Rejected):
                    preflight.docker_argv([arg for arg in args if arg != mandatory], False, cpu, pids)
        with self.assertRaisesRegex(preflight.Rejected, "^docker_command_not_allowed$"):
            preflight.docker_argv(preflight.verifier_run_args(name, image, False, False))

    def test_runtime_failure_does_not_retry_without_supported_resource_limits(self):
        capabilities = {"cpu_period": True, "cpu_quota": True, "pids": True, "memory": True}
        failed = subprocess.CompletedProcess([], 1, stdout=b"", stderr=b"test-only-private-runtime-error")
        output = io.StringIO()
        with patch.object(preflight, "docker_command", side_effect=[json.dumps(capabilities), "sha256:" + "a" * 64]), \
                patch.object(preflight.subprocess, "run", return_value=failed) as run, \
                contextlib.redirect_stdout(output), \
                self.assertRaisesRegex(preflight.Rejected, "^verifier_start_unconfirmed$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")
        run.assert_called_once()
        self.assertIn("--cpus=1", run.call_args.args[0])
        self.assertIn("--pids-limit=64", run.call_args.args[0])
        self.assertEqual(output.getvalue(), "")

    def test_docker_sudo_uses_only_trusted_noninteractive_local_cli(self):
        with patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "trusted_executable", side_effect=lambda name: "/usr/bin/" + name):
            args = preflight.docker_argv(preflight.DOCKER_INFO_ARGS, True)
            resource_args = preflight.docker_argv(preflight.DOCKER_RESOURCE_INFO_ARGS, True)
        self.assertEqual(args, ["/usr/bin/sudo", "-n", "--", "/usr/bin/docker",
                               "--host=unix:///var/run/docker.sock", "info", "--format", "{{.ServerVersion}}"])
        self.assertNotIn("-S", args)
        self.assertNotIn("-E", args)
        self.assertEqual(resource_args[:5], args[:5])
        self.assertEqual(resource_args[5:], preflight.DOCKER_RESOURCE_INFO_ARGS)

    def test_docker_never_escalates_implicitly(self):
        with patch.object(preflight, "trusted_executable") as trusted:
            args = preflight.docker_argv(preflight.DOCKER_INFO_ARGS)
        trusted.assert_not_called()
        self.assertEqual(args[:2], ["docker", "--host=unix:///var/run/docker.sock"])

    def test_docker_allowlist_rejects_service_changes_secret_inspect_and_unhardened_runs(self):
        name = "scm-preflight-" + "b" * 32
        run = preflight.verifier_run_args(name, "sha256:" + "a" * 64)
        for args in (["restart", "asset-postgres"], ["stop", "asset-postgres"],
                     ["rm", "--force", "asset-postgres"], ["compose", "up", "-d"],
                     ["info", "--format", "{{json .}}"],
                     ["inspect", "asset-postgres"],
                     ["inspect", "--format", "{{json .Config.Env}}", "asset-postgres"],
                     run + ["--privileged"],
                     run[:-1] + ["print('test-only-private')"],
                     ["--volume=/var/run/docker.sock:/var/run/docker.sock"] + run,
                     [arg.replace("--user=10001:10001", "--user=0:0") for arg in run]):
            with self.subTest(operation=args[0]), patch.object(preflight, "trusted_executable") as trusted, \
                    self.assertRaises(preflight.Rejected):
                preflight.docker_argv(args, True)
            trusted.assert_not_called()

    def test_sudo_executable_missing_or_untrusted_fails_before_execution(self):
        with patch.object(preflight.shutil, "which", return_value=None), \
                self.assertRaisesRegex(preflight.Rejected, "^docker_sudo_executable_missing$"):
            preflight.trusted_executable("sudo")
        for mode, uid in ((0o100777, 0), (0o100755, 1000)):
            resolved = SimpleNamespace(stat=lambda: SimpleNamespace(st_mode=mode, st_uid=uid))
            with self.subTest(mode=mode, uid=uid), patch.object(preflight.shutil, "which", return_value="/untrusted"), \
                    patch.object(preflight.Path, "resolve", return_value=resolved), \
                    self.assertRaisesRegex(preflight.Rejected, "^docker_sudo_executable_untrusted$"):
                preflight.trusted_executable("docker")

    def test_daemon_environment_drops_remote_context_and_secret_variables(self):
        with patch.dict(os.environ, {"DOCKER_HOST": "tcp://other-host:2375", "DOCKER_CONTEXT": "other",
                                     "DOCKER_CONFIG": "/other/config", "SCM_HANDOFF_KEY": "test-only-private",
                                     "SUDO_ASKPASS": "/other/helper"}):
            env = preflight.docker_environment()
        self.assertFalse(any(key.startswith(("DOCKER_", "SCM_", "COMPOSE_", "VITE_")) for key in env))
        self.assertNotIn("SUDO_ASKPASS", env)

    def test_sudo_auth_denial_stops_before_state_probes_and_prints_no_raw_output(self):
        failed = subprocess.CompletedProcess([], 1, stdout=b"test-only-private", stderr=b"test-only-private")
        output = io.StringIO()
        with patch.object(sys, "argv", ["preflight.py", "--docker-sudo", "--isolated-image", "local-verifier"]), \
                patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "compose_config", return_value=config()), \
                patch.object(preflight, "trusted_executable", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(preflight.subprocess, "run", return_value=failed) as run, \
                patch.object(preflight, "protected_state") as state, \
                patch.object(preflight, "isolated_runtime_checks") as runtime, contextlib.redirect_stdout(output):
            self.assertEqual(preflight.main(), 1)
        self.assertTrue(output.getvalue().endswith("FAIL docker_sudo_command_failed\n"))
        self.assertNotIn("test-only-private", output.getvalue())
        state.assert_not_called()
        runtime.assert_not_called()
        run.assert_called_once()
        self.assertNotIn("input", run.call_args.kwargs)

    def test_config_only_ignores_sudo_and_keeps_compose_unprivileged(self):
        with patch.object(sys, "argv", ["preflight.py", "--config-only", "--docker-sudo"]), \
                patch.object(preflight, "compose_config", return_value=config()), \
                patch.object(preflight, "trusted_executable") as trusted, \
                patch.object(preflight, "docker_command") as docker, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(preflight.main(), 0)
        trusted.assert_not_called()
        docker.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX file permissions required")
    def test_env_owner_and_600_checks_cannot_be_bypassed_by_sudo_user(self):
        with tempfile.TemporaryDirectory(prefix="scm-owner-test-") as directory:
            path = Path(directory) / ".env"
            path.write_text("# synthetic fixture only\n", encoding="utf-8")
            path.chmod(0o600)
            uid = path.stat().st_uid
            with patch.dict(os.environ, {"SUDO_UID": str(uid), "SUDO_USER": "test-owner"}), \
                    patch.object(preflight.os, "geteuid", return_value=uid + 1), \
                    patch.object(preflight, "command") as command, \
                    self.assertRaisesRegex(preflight.Rejected, "^env_owner_must_be_current_user$"):
                preflight.compose_config(env_file=path)
            command.assert_not_called()
            path.chmod(0o644)
            with patch.object(preflight, "command") as command, \
                    self.assertRaisesRegex(preflight.Rejected, "^env_mode_must_be_600$"):
                preflight.compose_config(env_file=path)
            command.assert_not_called()
            self.assertEqual(path.read_text(encoding="utf-8"), "# synthetic fixture only\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_host_queries_receive_sudo_but_listener_query_does_not(self):
        with patch.object(preflight.shutil, "which", return_value="/usr/bin/ss"), \
                patch.object(preflight, "command", return_value="LISTEN 0 1 127.0.0.1:3010 0.0.0.0:*\nLISTEN 0 1 127.0.0.1:8010 0.0.0.0:*") as command, \
                patch.object(preflight, "docker_command", return_value="container-snapshot") as docker:
            preflight.protected_state(True)
        command.assert_called_once_with(["ss", "-lntp"])
        docker.assert_called_once_with(["inspect", "--format", preflight.POSTGRES_STATE_FORMAT, "asset-postgres"], True)
        outputs = [json.dumps({"bridge": {}}), json.dumps([{"Gateway": "172.17.0.1"}]),
                   json.dumps({"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "15432"}]})]
        with patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "docker_command", side_effect=outputs) as docker:
            preflight.host_docker_checks(True)
        self.assertEqual(docker.call_count, 3)
        self.assertTrue(all(call.args[1] is True for call in docker.call_args_list))

    def test_sudo_verifier_keeps_payload_on_stdin_and_nonroot_container(self):
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        result = subprocess.CompletedProcess([], 0, stdout=worker_output(), stderr=b"")
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "trusted_executable", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(preflight, "docker_command", return_value="sha256:" + "a" * 64) as query, \
                patch.object(preflight.subprocess, "run", return_value=result) as run:
            preflight.isolated_runtime_checks(url, "local-verifier", True)
        self.assertEqual(query.call_args.args[1], True)
        args = run.call_args.args[0]
        self.assertEqual(args[:5], ["/usr/bin/sudo", "-n", "--", "/usr/bin/docker",
                                   "--host=unix:///var/run/docker.sock"])
        self.assertIn("--user=10001:10001", args)
        self.assertNotIn(url, " ".join(args))
        self.assertEqual(set(json.loads(run.call_args.kwargs["input"])), {"database_url", "script_sha256"})
        run.assert_called_once()

    def test_sudo_timeout_cleanup_failure_is_fixed_and_targets_only_its_verifier(self):
        failed = subprocess.CompletedProcess([], 1, stdout=b"private", stderr=b"private")
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "trusted_executable", side_effect=lambda name: "/usr/bin/" + name), \
                patch.object(preflight, "docker_command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", side_effect=[subprocess.TimeoutExpired("docker", 90), failed]) as run, \
                contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(preflight.Rejected, "^docker_cli_timeout$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier", True)
        start, cleanup = [call.args[0] for call in run.call_args_list]
        name = next(arg.split("=", 1)[1] for arg in start if arg.startswith("--name="))
        self.assertEqual(cleanup, start[:5] + ["rm", "--force", name])

    def test_local_tunnel_configuration_passes(self):
        preflight.validate_config(config())

    def test_config_policy_runs_without_site_packages_or_backend_imports(self):
        source = Path(preflight.__file__).read_text(encoding="utf-8")
        ast.parse(source, feature_version=(3, 8))
        code = ("import runpy,json,sys; "
                "module=runpy.run_path(sys.argv[1]); "
                "module['validate_config'](json.load(sys.stdin)); "
                "assert not any(n.startswith(('sqlalchemy','httpx','psycopg','app.')) for n in sys.modules)")
        result = subprocess.run([sys.executable, "-S", "-B", "-c", code, preflight.__file__],
                                input=json.dumps(config()), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "stdlib-only config check failed (output suppressed)")

    def test_stdlib_database_policy_rejects_overrides_wrong_targets_and_missing_password(self):
        for url in ("", None, "invalid-url", "postgresql://new_scm_ro:test-only@localhost/new_scm_dev",
                    "postgresql+psycopg://postgres:test-only@localhost/new_scm_dev",
                    "postgresql+psycopg://new_scm_ro:test-only@localhost/asset_manager_prod",
                    "postgresql+psycopg://new_scm_ro:test-only@localhost/new_scm_dev?user=postgres",
                    "postgresql+psycopg://new_scm_ro:test-only@localhost/new_scm_dev#fragment",
                    "postgresql+psycopg://new_scm_ro@localhost/new_scm_dev",
                    "postgresql+psycopg://new_scm_ro:test-only@localhost:bad/new_scm_dev"):
            with self.subTest(case=url), self.assertRaises(preflight.Rejected):
                preflight.validated_database_url(url)

    def test_origins_reject_private_http_cross_host_and_production_http(self):
        cases = (
            ("development", "http://192.168.222.210:3010", "http://127.0.0.1:8011",
             "browser_http_requires_local_tunnel"),
            ("development", "http://localhost:3010", "http://127.0.0.1:8011",
             "handoff_requires_same_site_browser_origins"),
            ("production", "https://asset.example", "https://scm.example",
             "handoff_requires_same_site_browser_origins"),
            ("production", "http://127.0.0.1:3010", "http://127.0.0.1:8011",
             "production_requires_https"),
        )
        for mode, source, destination, code in cases:
            candidate = config()
            candidate["services"]["backend"]["environment"].update(
                SCM_ENV=mode, SCM_HANDOFF_ORIGIN=source, SCM_FRONTEND_ORIGIN=destination)
            with self.subTest(mode=mode, source=source), self.assertRaisesRegex(preflight.Rejected, code):
                preflight.validate_config(candidate)

    def test_production_accepts_same_https_host_with_different_ports(self):
        candidate = config()
        candidate["services"]["backend"]["environment"].update(
            SCM_ENV="production", SCM_HANDOFF_ORIGIN="https://portal.example:443",
            SCM_FRONTEND_ORIGIN="https://portal.example:8443")
        preflight.validate_config(candidate)

    def test_command_errors_expose_only_fixed_codes(self):
        for exc, code in ((FileNotFoundError("test-only-private-value"), "required_command_missing"),
                          (subprocess.TimeoutExpired("test-only-private-value", 1),
                           "command_timeout_output_suppressed"),
                          (PermissionError("test-only-private-value"), "command_unavailable_output_suppressed")):
            with self.subTest(code=code), patch.object(preflight.subprocess, "run", side_effect=exc), \
                    self.assertRaisesRegex(preflight.Rejected, "^" + code + "$"):
                preflight.command(["missing-tool"])

    def test_main_keeps_unexpected_errors_and_malformed_config_private(self):
        for value, code in ((RuntimeError("test-only-private-value"), "preflight_unavailable_details_suppressed"),
                            ({}, "configuration_structure_invalid")):
            output = io.StringIO()
            kwargs = {"side_effect": value} if isinstance(value, Exception) else {"return_value": value}
            with patch.object(sys, "argv", ["preflight.py", "--config-only"]), \
                    patch.object(preflight, "compose_config", **kwargs), contextlib.redirect_stdout(output):
                self.assertEqual(preflight.main(), 1)
            self.assertEqual(output.getvalue(), "FAIL " + code + "\n")

    def test_config_only_never_starts_runtime_or_docker_probe(self):
        with patch.object(sys, "argv", ["preflight.py", "--config-only"]), \
                patch.object(preflight, "compose_config", return_value=config()), \
                patch.object(preflight, "host_checks") as host, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(preflight.main(), 0)
            host.assert_not_called()

    def test_config_only_cannot_start_an_isolated_image(self):
        with patch.object(sys, "argv", ["preflight.py", "--config-only", "--isolated-image", "local-image"]), \
                patch.object(preflight, "compose_config") as compose, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(preflight.main(), 1)
            compose.assert_not_called()

    def test_isolated_launcher_passes_only_db_url_via_stdin_without_socket_mount_or_ports(self):
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        image_id = "sha256:" + "a" * 64
        result = subprocess.CompletedProcess([], 0, stdout=worker_output(), stderr=b"")
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight, "command", return_value=image_id) as command, \
                patch.object(preflight.subprocess, "run", return_value=result) as run:
            preflight.isolated_runtime_checks(url, "local-verifier")
        self.assertEqual(command.call_count, 1)
        self.assertEqual(command.call_args.args[0], ["docker", "--host=unix:///var/run/docker.sock",
                         "image", "inspect", "--format", "{{.Id}}", "local-verifier"])
        args = run.call_args_list[0].args[0]
        for flag in ("--rm", "--pull=never", "--network=host", "--read-only", "--cap-drop=ALL", "--log-driver=none"):
            self.assertIn(flag, args)
        for flag in ("--volume", "-v", "--mount", "--env", "-e", "--env-file", "--publish", "-p", "--privileged"):
            self.assertNotIn(flag, args)
        self.assertNotIn(url, " ".join(args))
        payload = json.loads(run.call_args_list[0].kwargs["input"])
        self.assertEqual(set(payload), {"database_url", "script_sha256"})
        self.assertEqual(payload["database_url"], url)
        name = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--name="))
        self.assertTrue(name.startswith("scm-preflight-"))
        run.assert_called_once()  # --rm handles a normally completed worker.

    def test_isolated_timeout_cleans_up_only_its_unique_verifier(self):
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight, "command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", side_effect=[subprocess.TimeoutExpired("docker", 90),
                             subprocess.CompletedProcess([], 0)]) as run, \
                self.assertRaisesRegex(preflight.Rejected, "^docker_cli_timeout$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")
        args = run.call_args_list[0].args[0]
        name = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--name="))
        self.assertEqual(run.call_args_list[1].args[0], ["docker", "--host=unix:///var/run/docker.sock",
                                                       "rm", "--force", name])

    def test_isolated_docker_output_is_never_forwarded(self):
        result = subprocess.CompletedProcess([], 1, stdout=b"test-only-private-value", stderr=b"private")
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight, "command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", return_value=result), \
                self.assertRaisesRegex(preflight.Rejected, "^verifier_start_unconfirmed$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")

    def test_isolated_known_policy_failure_retains_only_its_fixed_code(self):
        result = subprocess.CompletedProcess([], preflight.WORKER_POLICY_EXIT,
                                             stdout=worker_output("FAIL expected_54_tables"), stderr=b"private")
        with patch.object(preflight, "verifier_resource_limits", return_value=(True, True)), \
                patch.object(preflight, "command", return_value="sha256:" + "a" * 64), \
                patch.object(preflight.subprocess, "run", return_value=result), \
                self.assertRaisesRegex(preflight.Rejected, "^expected_54_tables$"):
            preflight.isolated_runtime_checks("test-only-url", "local-verifier")

    def test_runtime_checks_use_only_readonly_db_queries_and_api_gets(self):
        def result(value):
            return SimpleNamespace(one=lambda: value, scalar_one=lambda: value,
                                   scalars=lambda: SimpleNamespace(all=lambda: value))
        engine = MagicMock()
        db = engine.connect.return_value.__enter__.return_value
        db.execute.side_effect = [result(("new_scm_dev", "new_scm_ro", "on")), result(54),
                                  result(["20261027_0013"]), result(0), result(0), result(False),
                                  result("admin"), result((1, "test-only-hash")), result((1, "test-only-hash"))]
        response = SimpleNamespace(status_code=200, json=lambda: {"paths": {
            "/auth/scm-handoff/issue": {"post": {}}, "/auth/scm-handoff/exchange": {"post": {}}}})
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        with patch("sqlalchemy.create_engine", return_value=engine) as create, \
                patch("app.db.identity.load_identity", return_value=(SimpleNamespace(id=1),
                      [("action", "system.access")])), patch("httpx.Client") as http:
            client = http.return_value.__enter__.return_value
            client.get.return_value = response
            preflight.runtime_checks(url)
        target = create.call_args.args[0]
        self.assertEqual((target.host, target.port, target.username, target.database),
                         ("127.0.0.1", 15432, "new_scm_ro", "new_scm_dev"))
        self.assertIn("default_transaction_read_only=on", create.call_args.kwargs["connect_args"]["options"])
        self.assertTrue(all(str(call.args[0]).strip().upper().startswith("SELECT ")
                            for call in db.execute.call_args_list))
        self.assertEqual([call.args[0] for call in client.get.call_args_list],
                         ["http://127.0.0.1:8010/openapi.json", "http://172.17.0.1:8010/openapi.json"])
        client.post.assert_not_called()
        db.rollback.assert_called_once()
        engine.dispose.assert_called_once()

    def test_runtime_checks_stop_before_table_queries_when_identity_is_wrong(self):
        engine = MagicMock()
        db = engine.connect.return_value.__enter__.return_value
        db.execute.return_value.one.return_value = ("other_database", "postgres", "off")
        url = config()["services"]["backend"]["environment"]["SCM_DATABASE_URL"]
        with patch("sqlalchemy.create_engine", return_value=engine), patch("httpx.Client") as http, \
                self.assertRaisesRegex(preflight.Rejected, "^database_identity_or_readonly_invalid$"):
            preflight.runtime_checks(url)
        db.execute.assert_called_once()
        http.assert_not_called()
        engine.dispose.assert_called_once()

    def test_worker_rejects_stale_image_before_any_db_connection(self):
        output = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(json.dumps({"script_sha256": "old-version", "database_url": "test-only-url"}))), \
                patch.object(preflight, "runtime_checks") as runtime, contextlib.redirect_stdout(output):
            self.assertEqual(preflight.isolated_worker(), preflight.WORKER_POLICY_EXIT)
            runtime.assert_not_called()
        self.assertEqual(output.getvalue(), "FAIL verifier_script_mismatch\n")

    def test_worker_returns_no_probe_values_or_exception_details(self):
        payload = {"script_sha256": preflight.script_digest(),
                   "database_url": "test-only-url"}
        for error, expected in ((None, "PASS isolated_db_api_checks\n"),
                                (RuntimeError("test-only-private-value"), "FAIL verifier_python_exception\n")):
            output = io.StringIO()
            with patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                    patch.object(preflight, "runtime_checks", side_effect=error) as runtime, \
                    contextlib.redirect_stdout(output):
                self.assertEqual(preflight.isolated_worker(), preflight.WORKER_EXCEPTION_EXIT if error else 0)
                runtime.assert_called_once_with(payload["database_url"])
            self.assertEqual(output.getvalue(), expected)

    def test_host_state_is_compared_even_when_runtime_probe_fails(self):
        with patch.object(preflight.sys, "platform", "linux"), \
                patch.object(preflight, "protected_state", side_effect=[b"before", b"after"]) as state, \
                patch.object(preflight, "host_docker_checks"), \
                patch.object(preflight, "runtime_checks", side_effect=RuntimeError("test-only-private-value")), \
                self.assertRaisesRegex(preflight.Rejected, "^protected_listeners_or_postgres_state_changed$"):
            preflight.host_checks({}, "test-only-url")
        self.assertEqual(state.call_count, 2)

    def test_old_host_python_gets_explicit_runtime_requirement(self):
        with patch.object(preflight.sys, "version_info", (3, 8, 15)), \
                self.assertRaisesRegex(preflight.Rejected, "^runtime_checks_require_python_3_12$"):
            preflight.runtime_checks("test-only-url")

    def test_identity_gateway_accepts_compose_output_formats(self):
        for extra_hosts in ({"nas-host": "172.17.0.1"},
                            ["nas-host:172.17.0.1"],
                            ["nas-host=172.17.0.1"]):
            with self.subTest(extra_hosts=extra_hosts):
                candidate = config()
                candidate["services"]["backend"]["extra_hosts"] = extra_hosts
                preflight.validate_config(candidate)

    def test_identity_gateway_rejects_wrong_missing_and_duplicate_mappings(self):
        rejected = (
            None, {}, [], "nas-host=172.17.0.1",
            {"other-host": "172.17.0.1"},
            {"nas-host": "172.17.0.2"},
            {"nas-host": "host-gateway"},
            {"nas-host": ["172.17.0.1"]},
            {"nas-host": "172.17.0.1", "other-host": "172.17.0.1"},
            ["nas-host:172.17.0.1", "nas-host:172.17.0.1"],
            ["nas-host=172.17.0.1", "nas-host=172.17.0.1"],
            ["nas-host:172.17.0.1", "nas-host=172.17.0.1"],
            ["nas-host=172.17.0.1", "nas-host=172.17.0.2"],
            ["nas-host=172.17.0.1", "other-host=172.17.0.1"],
            ["nas-host=172.17.0.1 "],
            [{"nas-host": "172.17.0.1"}],
        )
        for separator in (":", "="):
            for host, ip in (("other-host", "172.17.0.1"),
                             ("NAS-HOST", "172.17.0.1"),
                             ("nas-host", "172.17.0.2"),
                             ("nas-host", "127.0.0.1"),
                             ("nas-host", "host-gateway"),
                             ("nas-host", "")):
                rejected += ([f"{host}{separator}{ip}"],)
        for extra_hosts in rejected:
            with self.subTest(extra_hosts=extra_hosts):
                candidate = config()
                candidate["services"]["backend"]["extra_hosts"] = extra_hosts
                with self.assertRaisesRegex(preflight.Rejected, "^identity_gateway_invalid$"):
                    preflight.validate_config(candidate)

    def test_policy_rejects_public_port_wrong_role_origins_and_missing_secrets(self):
        for field, value in (("SCM_BIND_HOST", "0.0.0.0"), ("SCM_HTTP_PORT", "3010"),
                             ("SCM_HANDOFF_ORIGIN", "http://127.0.0.1:5173"),
                             ("SCM_HANDOFF_ORIGIN", "http://localhost:3010"),
                             ("SCM_FRONTEND_ORIGIN", "http://nas.example:8011"),
                             ("SCM_HANDOFF_KEY", ""), ("SCM_CORS_ORIGINS", "*")):
            candidate = config()
            candidate["services"]["backend"]["environment"][field] = value
            with self.subTest(field=field), self.assertRaises(preflight.Rejected):
                preflight.validate_config(candidate)
        for service in ("backend", "db-relay"):
            candidate = config()
            candidate["services"][service]["ports"] = [{"published": "8012"}]
            with self.assertRaises(preflight.Rejected):
                preflight.validate_config(candidate)

    @unittest.skipUnless(os.getenv("SCM_TEST_COMPOSE"), "standalone Compose not supplied")
    def test_real_compose_2_20_1_with_synthetic_env(self):
        env = copy.deepcopy(config()["services"]["backend"]["environment"])
        for name in ("SCM_DATABASE_SOCKET_DIR",):
            env.pop(name)
        with tempfile.TemporaryDirectory(prefix="scm-compose-test-") as directory:
            path = Path(directory) / ".env"
            path.write_text("\n".join(f"{key}={value}" for key, value in env.items()) + "\n", encoding="utf-8")
            path.chmod(0o600)
            resolved = preflight.compose_config(os.environ["SCM_TEST_COMPOSE"], path)
            preflight.validate_config(resolved)
            self.assertEqual(resolved["services"]["backend"]["volumes"][0]["read_only"], True)
            self.assertEqual(resolved["services"]["db-relay"]["entrypoint"], ["python", "-m", "app.db.relay"])
            self.assertNotIn("asset-postgres", resolved["services"])


if __name__ == "__main__":
    unittest.main()
