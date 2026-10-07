"""Isolated process and build-failure checks; these never touch NAS services."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
GIT_BASH = Path("C:/Program Files/Git/bin/bash.exe")
GIT_CYGPATH = Path("C:/Program Files/Git/usr/bin/cygpath.exe")
GIT_AWK = Path("C:/Program Files/Git/usr/bin/awk.exe")
BASH = str(GIT_BASH) if GIT_BASH.exists() else shutil.which("bash")
CYGPATH = str(GIT_CYGPATH) if GIT_CYGPATH.exists() else shutil.which("cygpath")
AWK = str(GIT_AWK) if GIT_AWK.exists() else shutil.which("awk")


def shell_path(path):
    if os.name != "nt":
        return str(path)
    if not CYGPATH:
        raise unittest.SkipTest("Git Bash cygpath is required on Windows")
    return subprocess.check_output([CYGPATH, "-u", str(path)], text=True, encoding="utf-8").strip()


@unittest.skipUnless(BASH, "bash is required")
class DirectDeploySafetyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("deploy", "logs", "backend/.venv/bin", "backend/app", "frontend/dist", "bin"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        (self.root / "backend/.venv/bin/activate").write_text('PATH="$NAS_PROJECT_DIR/bin:$PATH"; export PATH\n', encoding="utf-8")
        (self.root / "backend/app/main.py").write_text("app = object()\n", encoding="utf-8")
        (self.root / "frontend/package.json").write_text("{}\n", encoding="utf-8")
        (self.root / "frontend/package-lock.json").write_text("{}\n", encoding="utf-8")
        (self.root / "frontend/dist/index.html").write_text("PREVIOUS_DIST\n", encoding="utf-8")
        (self.root / "deploy/test.env").write_text(
            "NAS_PROJECT_DIR='{}'\nBACKEND_PORT=8010\n".format(shell_path(self.root)), encoding="utf-8"
        )
        self.env = os.environ.copy()
        self.env["ASSET_MANAGER_ENV"] = shell_path(self.root / "deploy/test.env")
        shell_search_path = subprocess.check_output([BASH, "-c", 'printf %s "$PATH"'], text=True, encoding="utf-8")
        self.env["PATH"] = shell_path(self.root / "bin") + ":" + shell_search_path

    def write(self, relative_path, content):
        path = self.root / relative_path
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    def init_git_checkout(self):
        (self.root / ".gitignore").write_text(
            "bin/\nlogs/\nbackend/.venv/\nfrontend/dist/\nfrontend/node_modules/\n"
            "deploy/test.env\ndeploy/.migration.env\ndeploy/*.sh\nfirst-build-failed\nstarted\nstopped\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        subprocess.run(["git", "-C", str(self.root), "add", ".gitignore", "frontend/package.json", "frontend/package-lock.json", "backend/app/main.py"], check=True)
        subprocess.run([
            "git", "-C", str(self.root), "-c", "user.name=Deploy Test", "-c", "user.email=deploy-test@example.invalid",
            "commit", "-qm", "test checkout",
        ], check=True)

    def run_script(self, filename, *args, extra_env=None):
        env = self.env.copy()
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [BASH, shell_path(REPO / "deploy" / filename), *args],
            cwd=REPO, env=env, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=20,
        )

    def mock_backend_processes(self):
        self.write("deploy/backend_process.sh", """
backend_pid_matches() { [ -f "$TEST_ALIVE_FILE" ] && [ "$1" = "4242" ]; }
backend_listener_pids() { printf '%s\\n' "${TEST_LISTENER_PID:-}"; }
backend_ps_pids() { printf '%s\\n' "${TEST_PS_PID:-}"; }
backend_port_status() { [ -f "$TEST_ALIVE_FILE" ]; }
kill() {
  if [ "$1" = "-0" ]; then [ -f "$TEST_ALIVE_FILE" ]; return; fi
  printf '%s\\n' "$*" >> "$TEST_EVENTS"
  rm -f "$TEST_ALIVE_FILE"
}
""")
        return {
            "TEST_ALIVE_FILE": shell_path(self.root / "alive"),
            "TEST_EVENTS": shell_path(self.root / "events"),
        }

    def test_stop_backend_finds_verified_listener_without_pid_file(self):
        extra = self.mock_backend_processes()
        (self.root / "alive").touch()
        extra["TEST_LISTENER_PID"] = "4242"
        result = self.run_script("stop_backend.sh", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4242", (self.root / "events").read_text(encoding="utf-8"))

    def test_stop_backend_finds_verified_listener_after_stale_pid_file(self):
        extra = self.mock_backend_processes()
        (self.root / "alive").touch()
        (self.root / "logs/backend.pid").write_text("9999\n", encoding="utf-8")
        extra["TEST_LISTENER_PID"] = "4242"
        result = self.run_script("stop_backend.sh", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4242", (self.root / "events").read_text(encoding="utf-8"))
        self.assertFalse((self.root / "logs/backend.pid").exists())

    @unittest.skipUnless(AWK, "awk is required")
    def test_backend_command_matcher_awk_accepts_only_target_app_and_port(self):
        source = (REPO / "deploy/backend_process.sh").read_text(encoding="utf-8")
        program = source.split('awk -v port="$BACKEND_PORT" \'', 1)[1].split("\n  '\n", 1)[0]
        cases = (
            ("python3.8\n-m\nuvicorn\napp.main:app\n--port\n8010\n", 0),
            ("python3.8\n-m\nuvicorn\napp.main:app\n--port\n8011\n", 1),
            ("python3.8\n-m\nuvicorn\napp.main:app\n--port\n8010\n--port\n8011\n", 1),
            ("python3.8\n-m\nhttp.server\napp.main:app\n--port\n8010\n", 1),
            ("python3.8\n-m\nuvicorn\nother.main:app\n--port\n8010\n", 1),
        )
        for tokens, expected in cases:
            with self.subTest(tokens=tokens):
                result = subprocess.run([AWK, "-v", "port=8010", program], input=tokens, text=True, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)

    def test_backend_matcher_does_not_require_cwd_or_kill_probe(self):
        source = (REPO / "deploy/backend_process.sh").read_text(encoding="utf-8")
        matcher = source.split("backend_pid_matches() {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("readlink", matcher)
        self.assertNotIn("/cwd", matcher.split("#", 1)[0])
        self.assertNotIn("kill -0", matcher.split("#", 1)[0])

        cmdline = self.root / "cmdline"
        cmdline.write_bytes(b"python3.8\0-m\0uvicorn\0app.main:app\0--port\08010\0")
        env = self.env.copy()
        env.update({"BACKEND_PORT": "8010", "TEST_CMDLINE": shell_path(cmdline), "TEST_HELPER": shell_path(REPO / "deploy/backend_process.sh")})
        result = subprocess.run(
            [BASH, "-c", '. "$TEST_HELPER"; readlink() { return 1; }; kill() { return 1; }; backend_cmdline_matches "$TEST_CMDLINE"'],
            env=env, text=True, encoding="utf-8", errors="replace", capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(AWK, "awk is required")
    def test_frontend_command_matcher_awk_requires_3010(self):
        source = (REPO / "deploy/frontend_process.sh").read_text(encoding="utf-8")
        program = source.split('awk -v script="$frontend_script"', 1)[1].split("'\n", 1)[1].split("\n    '\n", 1)[0]
        tokens = "python3\n/deploy/static_server.py\n--port\n3010\n--directory\n/frontend/dist\n"
        command = [AWK, "-v", "script=/deploy/static_server.py", "-v", "directory=/frontend/dist", "-v", "port=3010", program]
        good = subprocess.run(command, input=tokens, text=True, capture_output=True)
        bad = subprocess.run(command, input=tokens.replace("3010", "3011"), text=True, capture_output=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertNotEqual(bad.returncode, 0)

    def test_stop_backend_ignores_stale_pid_and_unrelated_listener(self):
        extra = self.mock_backend_processes()
        (self.root / "alive").touch()
        (self.root / "logs/backend.pid").write_text("9999\n", encoding="utf-8")
        extra["TEST_LISTENER_PID"] = "9999"
        result = self.run_script("stop_backend.sh", extra_env=extra)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrelated", result.stdout.lower())
        self.assertFalse((self.root / "events").exists())

    def test_stop_frontend_leaves_unrelated_3010_listener_running(self):
        self.write("deploy/frontend_process.sh", """
frontend_pid_matches() { return 1; }
frontend_port_status() { return 0; }
frontend_listener_pids() { printf '7777\\n'; }
frontend_ps_pids() { :; }
kill() { printf '%s\\n' "$*" >> "$TEST_EVENTS"; }
""")
        (self.root / "logs/frontend.pid").write_text("7777\n", encoding="utf-8")
        result = self.run_script("stop_frontend.sh", extra_env={"TEST_EVENTS": shell_path(self.root / "events")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3010", result.stderr)
        self.assertFalse((self.root / "events").exists())

    def test_stop_frontend_finds_ps_candidate_without_pid_file(self):
        self.write("deploy/frontend_process.sh", """
frontend_pid_matches() { [ -f "$TEST_ALIVE_FILE" ] && [ "$1" = "5151" ]; }
frontend_listener_pids() { :; }
frontend_ps_pids() { printf '5151\\n'; }
frontend_port_status() { [ -f "$TEST_ALIVE_FILE" ]; }
kill() {
  if [ "$1" = "-0" ]; then [ -f "$TEST_ALIVE_FILE" ]; return; fi
  printf '%s\\n' "$*" >> "$TEST_EVENTS"
  rm -f "$TEST_ALIVE_FILE"
}
""")
        (self.root / "alive").touch()
        extra = {"TEST_ALIVE_FILE": shell_path(self.root / "alive"), "TEST_EVENTS": shell_path(self.root / "events")}
        result = self.run_script("stop_frontend.sh", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("5151", (self.root / "events").read_text(encoding="utf-8"))

    def test_start_backend_blocks_failed_import_before_launch(self):
        self.write("deploy/backend_process.sh", """
backend_pid_matches() { return 1; }
backend_port_status() { return 1; }
backend_listener_pids() { :; }
""")
        self.write("bin/python", "#!/bin/sh\nexit 1\n")
        result = self.run_script("start_backend.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("import check failed", result.stderr.lower())
        self.assertFalse((self.root / "logs/backend.pid").exists())

    def test_start_backend_drops_migration_url_before_import(self):
        self.write("deploy/backend_process.sh", """
backend_pid_matches() { return 1; }
backend_port_status() { return 1; }
backend_listener_pids() { :; }
""")
        with (self.root / "deploy/test.env").open("a", encoding="utf-8") as env_file:
            env_file.write("MIGRATION_DATABASE_URL=TEST_ONLY_SECRET\n")
        self.write("bin/python", """#!/bin/sh
if [ -n "${MIGRATION_DATABASE_URL:-}" ]; then echo MIGRATION_URL_LEAKED >&2; else echo MIGRATION_URL_CLEARED >&2; fi
exit 1
""")
        result = self.run_script("start_backend.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("MIGRATION_URL_CLEARED", result.stderr)
        self.assertNotIn("MIGRATION_URL_LEAKED", result.stderr)

    def test_missing_migration_env_fails_before_backend_stop(self):
        self.init_git_checkout()
        self.write("bin/python", "#!/bin/sh\nexit 0\n")
        self.write("bin/alembic", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/alembic-ran\"\n")
        self.write("deploy/stop_backend.sh", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/stopped\"\n")
        result = self.run_script("deploy.sh", "--no-pull", extra_env={"MIGRATION_DATABASE_URL": "TEST_ONLY_SECRET"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stage: BACKEND_PREPARE", result.stdout)
        self.assertIn("MIGRATION_DATABASE_URL is required", result.stdout)
        self.assertFalse((self.root / "alembic-ran").exists())
        self.assertFalse((self.root / "stopped").exists())

    def test_migration_url_only_reaches_alembic(self):
        self.init_git_checkout()
        (self.root / "deploy/.migration.env").write_text("MIGRATION_DATABASE_URL=TEST_ONLY_SECRET\n", encoding="utf-8")
        self.write("bin/python", """#!/bin/sh
[ -z "${MIGRATION_DATABASE_URL:-}" ] || exit 2
exit 0
""")
        self.write("bin/alembic", """#!/bin/sh
[ "$MIGRATION_DATABASE_URL" = "TEST_ONLY_SECRET" ] || exit 2
echo "$1" >> "$NAS_PROJECT_DIR/alembic-events"
""")
        self.write("bin/npm", """#!/bin/sh
[ -z "${MIGRATION_DATABASE_URL:-}" ] || exit 2
exit 1
""")
        result = self.run_script("deploy.sh", "--no-pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Stage: FRONTEND_BUILD", result.stdout)
        self.assertEqual((self.root / "alembic-events").read_text(encoding="utf-8").splitlines(), ["current", "heads", "upgrade"])
        self.assertNotIn("TEST_ONLY_SECRET", result.stdout + result.stderr)

    def test_failed_frontend_build_preserves_previous_dist_and_never_stops(self):
        self.init_git_checkout()
        (self.root / "deploy/.migration.env").write_text("MIGRATION_DATABASE_URL=TEST_ONLY_SECRET\n", encoding="utf-8")
        self.write("bin/python", """#!/bin/sh
case "$1" in -c) echo IMPORT_OK ;; esac
exit 0
""")
        self.write("bin/alembic", "#!/bin/sh\nexit 0\n")
        self.write("bin/npm", """#!/bin/sh
if [ "$1" = "run" ]; then echo "test build failure"; exit 1; fi
exit 0
""")
        self.write("deploy/stop_all.sh", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/stopped\"\n")
        result = self.run_script("deploy.sh", "--no-pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")
        self.assertFalse((self.root / "stopped").exists())

    def test_failed_stop_never_starts_backend_or_replaces_dist(self):
        self.init_git_checkout()
        (self.root / "deploy/.migration.env").write_text("MIGRATION_DATABASE_URL=TEST_ONLY_SECRET\n", encoding="utf-8")
        self.write("bin/python", "#!/bin/sh\nexit 0\n")
        self.write("bin/alembic", "#!/bin/sh\nexit 0\n")
        self.write("bin/npm", """#!/bin/sh
if [ "$1" = "run" ]; then
  if [ ! -f "$NAS_PROJECT_DIR/first-build-failed" ]; then
    touch "$NAS_PROJECT_DIR/first-build-failed"
    echo 'Cannot find module @rollup/rollup-linux-x64-gnu'
    exit 1
  fi
  mkdir -p "$5/assets"
  printf '<script type="module" src="/assets/index-test.js"></script><link rel="stylesheet" href="/assets/index-test.css">\\n' > "$5/index.html"
  printf 'ok\\n' > "$5/assets/index-test.js"
  printf 'body {}\\n' > "$5/assets/index-test.css"
fi
exit 0
""")
        self.write("deploy/stop_backend.sh", "#!/bin/sh\nexit 1\n")
        self.write("deploy/start_backend.sh", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/started\"\n")
        self.write("bin/smoke-node", "#!/bin/sh\necho BROWSER_PRECHECK >> \"$NAS_PROJECT_DIR/events\"\n")
        result = self.run_script("deploy.sh", "--no-pull", extra_env={"FRONTEND_SMOKE_NODE": shell_path(self.root / "bin/smoke-node")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Frontend build completed after Rollup optional dependency recovery.", result.stdout)
        self.assertIn("== Stop backend (frontend remains online) ==", result.stdout)
        self.assertIn("Stage: STOP_BACKEND", result.stdout)
        self.assertNotIn("Working tree is dirty", result.stdout)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")
        self.assertEqual((self.root / "frontend/package-lock.json").read_text(encoding="utf-8"), "{}\n")
        self.assertFalse(list((self.root / "frontend").glob("dist.next.*")))
        self.assertFalse((self.root / "started").exists())

    def test_stop_backend_finds_ps_candidate_without_pid_or_listener_pid(self):
        extra = self.mock_backend_processes()
        (self.root / "alive").touch()
        extra["TEST_PS_PID"] = "4242"
        result = self.run_script("stop_backend.sh", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("4242", (self.root / "events").read_text(encoding="utf-8"))

    def test_stop_backend_rejects_multiple_verified_candidates(self):
        extra = self.mock_backend_processes()
        self.write("deploy/backend_process.sh", (self.root / "deploy/backend_process.sh").read_text(encoding="utf-8").replace(
            '[ "$1" = "4242" ]', '( [ "$1" = "4242" ] || [ "$1" = "4343" ] )'
        ))
        (self.root / "alive").touch()
        extra["TEST_LISTENER_PID"] = "4242"
        extra["TEST_PS_PID"] = "4343"
        result = self.run_script("stop_backend.sh", extra_env=extra)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("4242 4343", result.stderr)
        self.assertFalse((self.root / "events").exists())

    def prepare_mock_deploy(self):
        self.init_git_checkout()
        (self.root / "deploy/.migration.env").write_text("MIGRATION_DATABASE_URL=TEST_ONLY_SECRET\n", encoding="utf-8")
        with (self.root / "deploy/test.env").open("a", encoding="utf-8") as env_file:
            env_file.write('kill() { [ "$1" = "-0" ] && [ "$2" = "$TEST_PID" ]; }\n')
        self.write("bin/python", "#!/bin/sh\necho IMPORT_OK\n")
        self.write("bin/alembic", "#!/bin/sh\nexit 0\n")
        self.write("bin/sleep", "#!/bin/sh\nexit 0\n")
        self.write("bin/npm", """#!/bin/sh
if [ "$1" = "run" ]; then
  mkdir -p "$5/assets"
  printf '<script type="module" src="/assets/index-new.js"></script><link rel="stylesheet" href="/assets/index-new.css">\\n' > "$5/index.html"
  printf 'new\\n' > "$5/assets/index-new.js"
  printf 'body {}\\n' > "$5/assets/index-new.css"
fi
exit 0
""")
        self.write("bin/smoke-node", """#!/bin/sh
if [ "$2" = "--check-browser" ]; then
  echo BROWSER_PRECHECK >> "$NAS_PROJECT_DIR/events"
  if [ "${TEST_BROWSER_UNAVAILABLE:-}" = "1" ]; then exit 2; fi
  if [ "${TEST_FAIL_STAGE:-}" = "BROWSER_PRECHECK" ]; then exit 2; fi
  if [ "${TEST_FAIL_STAGE:-}" = "BROWSER_LAUNCH" ]; then exit 1; fi
  exit 0
fi
echo BROWSER_SMOKE >> "$NAS_PROJECT_DIR/events"
if [ "${TEST_FAIL_STAGE:-}" = "BROWSER_SMOKE" ] && [ ! -f "$NAS_PROJECT_DIR/first-smoke-failed" ]; then
  touch "$NAS_PROJECT_DIR/first-smoke-failed"
  echo 'Uncaught ReferenceError: React is not defined' >&2
  exit 1
fi
exit 0
""")
        self.write("bin/curl", """#!/bin/sh
for argument do
  case "$argument" in
    *openapi.json)
      echo VERIFY_OPENAPI >> "$NAS_PROJECT_DIR/events"
      if [ "${TEST_FAIL_STAGE:-}" = "OPENAPI" ]; then printf '{"paths":{}}\\n'; else printf '{"paths":{"/online/recall/applications/preview":{}}}\\n'; fi
      exit 0 ;;
    *network/status) printf 'HTTP/1.1 200 OK\\r\\naccess-control-allow-origin: http://192.168.222.210:3010\\r\\naccess-control-allow-origin: http://112.216.230.162:3010\\r\\n'; exit 0 ;;
  esac
done
case " $* " in
  *" -w "*)
    if [ "${TEST_FAIL_STAGE:-}" = "BUNDLE_HTTP" ]; then
      case " $* " in *assets/index-new.js*) printf '404'; exit 0 ;; esac
    fi
    printf '200' ;;
  *) printf '<script type="module" src="/assets/index-new.js"></script><link rel="stylesheet" href="/assets/index-new.css">\\n' ;;
esac
""")
        self.write("deploy/stop_backend.sh", """#!/bin/sh
echo STOP_BACKEND >> "$NAS_PROJECT_DIR/events"
[ "${TEST_FAIL_STAGE:-}" != "STOP_BACKEND" ]
""")
        self.write("deploy/start_backend.sh", """#!/bin/sh
echo START_BACKEND >> "$NAS_PROJECT_DIR/events"
if [ "${TEST_FAIL_STAGE:-}" = "START_BACKEND" ]; then exit 1; fi
echo "$TEST_PID" > "$NAS_PROJECT_DIR/logs/backend.pid"
""")
        self.write("deploy/backend_process.sh", 'backend_pid_matches() { [ "$1" = "$TEST_PID" ]; }\n')
        self.write("deploy/stop_frontend.sh", """#!/bin/sh
echo STOP_FRONTEND >> "$NAS_PROJECT_DIR/events"
exit 0
""")
        self.write("deploy/start_frontend.sh", """#!/bin/sh
echo START_FRONTEND >> "$NAS_PROJECT_DIR/events"
if [ "${TEST_FAIL_STAGE:-}" = "START_FRONTEND" ] && [ ! -f "$NAS_PROJECT_DIR/first-build-failed" ]; then
  touch "$NAS_PROJECT_DIR/first-build-failed"
  exit 1
fi
echo "$TEST_PID" > "$NAS_PROJECT_DIR/logs/frontend.pid"
""")
        self.write("deploy/health_check.sh", "#!/bin/sh\necho HEALTH_CHECK >> \"$NAS_PROJECT_DIR/events\"\n")
        return {"TEST_PID": str(os.getpid()), "FRONTEND_SMOKE_NODE": shell_path(self.root / "bin/smoke-node")}

    def test_backend_stop_failure_preserves_running_frontend_and_dist(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "STOP_BACKEND"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: STOP_BACKEND", result.stdout)
        self.assertEqual((self.root / "events").read_text(encoding="utf-8").splitlines(), ["BROWSER_PRECHECK", "STOP_BACKEND"])
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    def test_backend_start_failure_does_not_stop_frontend(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "START_BACKEND"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: START_BACKEND", result.stdout)
        self.assertEqual((self.root / "events").read_text(encoding="utf-8").splitlines(), ["BROWSER_PRECHECK", "STOP_BACKEND", "START_BACKEND"])
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    def test_backend_openapi_failure_does_not_stop_frontend(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "OPENAPI"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: START_BACKEND", result.stdout)
        self.assertEqual((self.root / "events").read_text(encoding="utf-8").splitlines(), ["BROWSER_PRECHECK", "STOP_BACKEND", "START_BACKEND", "VERIFY_OPENAPI"])
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    def test_frontend_start_failure_restores_previous_dist(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "START_FRONTEND"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: FRONTEND_CUTOVER", result.stdout)
        events = (self.root / "events").read_text(encoding="utf-8").splitlines()
        self.assertEqual(events, ["BROWSER_PRECHECK", "STOP_BACKEND", "START_BACKEND", "VERIFY_OPENAPI", "STOP_FRONTEND", "START_FRONTEND", "STOP_FRONTEND", "START_FRONTEND", "BROWSER_SMOKE"])
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    def test_successful_deploy_starts_backend_before_frontend_cutover(self):
        extra = self.prepare_mock_deploy()
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        events = (self.root / "events").read_text(encoding="utf-8").splitlines()
        self.assertEqual(events, ["BROWSER_PRECHECK", "STOP_BACKEND", "START_BACKEND", "VERIFY_OPENAPI", "STOP_FRONTEND", "START_FRONTEND", "HEALTH_CHECK", "BROWSER_SMOKE", "VERIFY_OPENAPI"])
        self.assertIn("DEPLOY SUCCESS", result.stdout)
        self.assertIn("Browser Smoke Test: PASS", result.stdout)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), '<script type="module" src="/assets/index-new.js"></script><link rel="stylesheet" href="/assets/index-new.css">\n')
        self.assertFalse(list((self.root / "frontend").glob("dist.previous.*")))

    def test_browser_smoke_failure_rolls_back_and_never_succeeds(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "BROWSER_SMOKE"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: FRONTEND_BROWSER_SMOKE", result.stdout)
        self.assertIn("DEPLOY FAILED", result.stdout)
        self.assertNotIn("DEPLOY SUCCESS", result.stdout)
        self.assertIn("Previous frontend restored successfully.", result.stdout)
        self.assertIn("React is not defined", result.stdout)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")
        events = (self.root / "events").read_text(encoding="utf-8").splitlines()
        self.assertEqual(events.count("BROWSER_SMOKE"), 2)

    def test_missing_browser_skips_smoke_and_deploys(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "BROWSER_PRECHECK"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("WARNING Browser smoke test skipped", result.stdout)
        self.assertIn("Browser Smoke Test: SKIPPED (browser unavailable)", result.stdout)
        self.assertIn("DEPLOY SUCCESS", result.stdout)
        self.assertIn("Built frontend bundle:  assets/index-new.js", result.stdout)
        self.assertIn("Served frontend bundle: assets/index-new.js", result.stdout)
        self.assertEqual((self.root / "events").read_text(encoding="utf-8").splitlines(), ["BROWSER_PRECHECK", "STOP_BACKEND", "START_BACKEND", "VERIFY_OPENAPI", "STOP_FRONTEND", "START_FRONTEND", "HEALTH_CHECK", "VERIFY_OPENAPI"])

    def test_browser_launch_failure_stops_before_service_restart(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "BROWSER_LAUNCH"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Stage: FRONTEND_BROWSER_PRECHECK", result.stdout)
        self.assertIn("Browser Smoke Test: FAIL", result.stdout)
        self.assertEqual((self.root / "events").read_text(encoding="utf-8").splitlines(), ["BROWSER_PRECHECK"])
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    def test_bundle_http_failure_rolls_back_when_browser_is_skipped(self):
        extra = self.prepare_mock_deploy()
        extra["TEST_FAIL_STAGE"] = "BUNDLE_HTTP"
        extra["TEST_BROWSER_UNAVAILABLE"] = "1"
        result = self.run_script("deploy.sh", "--no-pull", extra_env=extra)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("DEPLOY FAILED", result.stdout)
        self.assertNotIn("DEPLOY SUCCESS", result.stdout)
        self.assertIn("Frontend JS bundle", result.stdout)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")

    @unittest.skipUnless(AWK, "awk is required")
    def test_ps_matchers_accept_paths_with_spaces_and_reject_other_processes(self):
        backend_source = (REPO / "deploy/backend_process.sh").read_text(encoding="utf-8")
        backend_program = backend_source.split('backend_ps_command_matches() {', 1)[1].split("awk -v port=\"$BACKEND_PORT\" '", 1)[1].split("\n  '\n", 1)[0]
        backend_command = [AWK, "-v", "port=8010", backend_program]
        for command, expected in (
            ("/volume6/asset manager/.venv/bin/python -m uvicorn app.main:app --port 8010", 0),
            ("python -m uvicorn app.main:app --port 8011", 1),
            ("python -m http.server app.main:app --port 8010", 1),
        ):
            with self.subTest(command=command):
                result = subprocess.run(backend_command, input=command + "\n", text=True, capture_output=True)
                self.assertEqual(result.returncode, expected, result.stderr)

        frontend_source = (REPO / "deploy/frontend_process.sh").read_text(encoding="utf-8")
        frontend_program = frontend_source.split('frontend_ps_command_matches() {', 1)[1].split("awk -v script=\"$frontend_script\" -v directory=\"$frontend_dist\" -v port=\"$FRONTEND_PORT\" '", 1)[1].split("\n  '\n", 1)[0]
        command = [AWK, "-v", "script=/volume6/asset manager/deploy/static_server.py", "-v", "directory=/volume6/asset manager/frontend/dist", "-v", "port=3010", frontend_program]
        good = "/volume6/asset manager/.venv/bin/python /volume6/asset manager/deploy/static_server.py --port 3010 --directory /volume6/asset manager/frontend/dist\n"
        self.assertEqual(subprocess.run(command, input=good, text=True, capture_output=True).returncode, 0)
        self.assertNotEqual(subprocess.run(command, input=good.replace("3010", "3011"), text=True, capture_output=True).returncode, 0)

    def test_untracked_source_blocks_before_dependency_install(self):
        self.init_git_checkout()
        source_file = self.root / "frontend/src/new-feature.jsx"
        source_file.parent.mkdir()
        source_file.write_text("source change\n", encoding="utf-8")
        self.write("bin/npm", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/npm-ran\"\n")
        result = self.run_script("deploy.sh", "--no-pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontend/src/new-feature.jsx", result.stdout)
        self.assertFalse((self.root / "npm-ran").exists())

    def test_tracked_source_blocks_before_dependency_install(self):
        self.init_git_checkout()
        (self.root / "frontend/package.json").write_text('{"changed": true}\n', encoding="utf-8")
        self.write("bin/npm", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/npm-ran\"\n")
        result = self.run_script("deploy.sh", "--no-pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("frontend/package.json", result.stdout)
        self.assertFalse((self.root / "npm-ran").exists())

    def test_git_excludes_only_the_exact_generated_directory(self):
        if not shutil.which("git"):
            self.skipTest("git is required")
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        candidate = self.root / "frontend/dist.next.123"
        candidate.mkdir()
        (candidate / "index.html").write_text("generated", encoding="utf-8")
        source_file = self.root / "frontend/src/new-feature.jsx"
        source_file.parent.mkdir()
        source_file.write_text("source", encoding="utf-8")
        result = subprocess.run(
            ["git", "-C", str(self.root), "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude,literal)frontend/dist.next.123"],
            check=True, text=True, encoding="utf-8", capture_output=True,
        )
        self.assertNotIn("frontend/dist.next.123", result.stdout)
        self.assertIn("frontend/src/new-feature.jsx", result.stdout)

    def test_full_deploy_has_one_migration_and_one_health_path(self):
        wrapper = (REPO / "deploy/full_deploy.sh").read_text(encoding="utf-8")
        deploy = (REPO / "deploy/deploy.sh").read_text(encoding="utf-8")
        self.assertNotIn("alembic upgrade", wrapper)
        self.assertNotIn("health_check.sh", wrapper)
        self.assertEqual(deploy.count("alembic upgrade head"), 1)
        self.assertEqual(deploy.count('"$ROOT_DIR/deploy/health_check.sh"'), 1)


if __name__ == "__main__":
    unittest.main()
