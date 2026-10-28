"""Offline image smoke check. No env files, Docker CLI, DB or API connections."""
import importlib
import os
from pathlib import Path
import runpy
import stat
import subprocess
import sys

ROOT = Path("/srv/new-scm")


def main():
    code = "verifier_image_uid_invalid"
    try:
        if (os.geteuid(), os.getegid()) != (10001, 10001):
            raise ValueError()
        code = "verifier_image_permissions_invalid"
        directories = [Path("/srv"), ROOT, ROOT / "deploy", ROOT / "backend",
                       ROOT / "backend/app", ROOT / "backend/app/db"]
        files = [ROOT / "deploy/preflight.py", ROOT / "deploy/check_preflight_image.py",
                 ROOT / "backend/app/db/identity.py"]
        for path, mode in [(p, 0o755) for p in directories] + [(p, 0o644) for p in files]:
            metadata = path.stat()
            if (metadata.st_uid, metadata.st_gid, stat.S_IMODE(metadata.st_mode)) != (0, 0, mode):
                raise ValueError()
        for path in files:
            compile(path.read_bytes(), str(path), "exec")
        code = "verifier_image_import_failed"
        module = runpy.run_path(str(files[0]))
        for name in ("app.db.identity", "sqlalchemy", "psycopg", "httpx"):
            importlib.import_module(name)
        code = "verifier_image_execution_failed"
        base = [sys.executable, "-I", "-B", str(files[0])]
        help_result = subprocess.run(base + ["--help"], capture_output=True, timeout=15)
        if help_result.returncode != 0:
            raise ValueError()
        # Invalid synthetic input must fail before any DB/API/Docker access.
        worker_result = subprocess.run(base + ["--isolated-worker"], input=b"{}",
                                       capture_output=True, timeout=15)
        if (worker_result.returncode != module["WORKER_POLICY_EXIT"]
                or worker_result.stdout.strip() != b"FAIL verifier_input_invalid"):
            raise ValueError()
        print("PASS verifier_image_nonroot_smoke")
        return 0
    except Exception:
        print("FAIL " + code)
        return 1


if __name__ == "__main__":
    sys.exit(main())
