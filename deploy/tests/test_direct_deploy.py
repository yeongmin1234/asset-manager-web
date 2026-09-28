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
        (self.root / "backend/.venv/bin/activate").write_text("# test venv\n", encoding="utf-8")
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
backend_pid_matches() { [ "$1" = "4242" ]; }
backend_listener_pids() { printf '%s\\n' "${TEST_LISTENER_PID:-}"; }
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

    @unittest.skipUnless(AWK, "awk is required")
    def test_backend_command_matcher_awk_accepts_only_matching_port(self):
        source = (REPO / "deploy/backend_process.sh").read_text(encoding="utf-8")
        program = source.split('awk -v port="$BACKEND_PORT" \'', 1)[1].split("\n  '\n", 1)[0]
        tokens = "python3.8\n-m\nuvicorn\napp.main:app\n--port\n8010\n"
        good = subprocess.run([AWK, "-v", "port=8010", program], input=tokens, text=True, capture_output=True)
        bad = subprocess.run([AWK, "-v", "port=3010", program], input=tokens, text=True, capture_output=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertNotEqual(bad.returncode, 0)

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
kill() { printf '%s\\n' "$*" >> "$TEST_EVENTS"; }
""")
        (self.root / "logs/frontend.pid").write_text("7777\n", encoding="utf-8")
        result = self.run_script("stop_frontend.sh", extra_env={"TEST_EVENTS": shell_path(self.root / "events")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("3010", result.stderr)
        self.assertFalse((self.root / "events").exists())

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

    def test_failed_frontend_build_preserves_previous_dist_and_never_stops(self):
        self.write("bin/git", """#!/bin/sh
case " $* " in
  *" log "*) echo "test commit" ;;
esac
exit 0
""")
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
        self.write("bin/git", "#!/bin/sh\nexit 0\n")
        self.write("bin/python", "#!/bin/sh\nexit 0\n")
        self.write("bin/alembic", "#!/bin/sh\nexit 0\n")
        self.write("bin/npm", """#!/bin/sh
if [ "$1" = "run" ]; then
  mkdir -p "$5/assets"
  printf '<script type="module" src="/assets/index-test.js"></script>\\n' > "$5/index.html"
  printf 'ok\\n' > "$5/assets/index-test.js"
fi
exit 0
""")
        self.write("deploy/stop_all.sh", "#!/bin/sh\nexit 1\n")
        self.write("deploy/start_backend.sh", "#!/bin/sh\ntouch \"$NAS_PROJECT_DIR/started\"\n")
        result = self.run_script("deploy.sh", "--no-pull")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "frontend/dist/index.html").read_text(encoding="utf-8"), "PREVIOUS_DIST\n")
        self.assertFalse((self.root / "started").exists())

    def test_full_deploy_has_one_migration_and_one_health_path(self):
        wrapper = (REPO / "deploy/full_deploy.sh").read_text(encoding="utf-8")
        deploy = (REPO / "deploy/deploy.sh").read_text(encoding="utf-8")
        self.assertNotIn("alembic upgrade", wrapper)
        self.assertNotIn("health_check.sh", wrapper)
        self.assertEqual(deploy.count("alembic upgrade head"), 1)
        self.assertEqual(deploy.count('"$ROOT_DIR/deploy/health_check.sh"'), 1)


if __name__ == "__main__":
    unittest.main()
