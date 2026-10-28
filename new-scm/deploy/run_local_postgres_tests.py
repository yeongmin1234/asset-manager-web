"""WSL development machine ONLY: disposable, network-none PostgreSQL tests.

Never connects to the NAS, publishes ports, mounts Docker sockets, or starts SCM.
Requires an already-cached PostgreSQL 16 image. No pull, sudo, or service restart.
"""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
import time
from uuid import uuid4

DOCKER = ["/usr/bin/docker", "--host=unix:///var/run/docker.sock"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-executable", required=True)
    parser.add_argument("--verifier-image")
    args = parser.parse_args()
    if sys.platform != "linux" or "microsoft" not in platform.release().lower():
        print("FAIL isolated_tests_require_local_wsl")
        return 1
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(("SCM_", "DOCKER_", "COMPOSE_", "VITE_", "DATABASE_"))}
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    def docker(arguments, **kwargs):
        return subprocess.run(DOCKER + arguments, env=environment, capture_output=True, timeout=30, **kwargs)
    name = "scm-i-test-" + uuid4().hex
    directory = None
    started = False
    removed_ok = False
    code = 1
    try:
        info = docker(["info", "--format", '{{json .OperatingSystem}}'])
        if info.returncode or not str(json.loads(info.stdout)).startswith("Ubuntu "):
            raise RuntimeError()
        found = docker(["image", "inspect", "--format", "{{.Id}}", "postgres:16-bookworm"])
        image = found.stdout.decode().strip()
        if found.returncode or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
            raise RuntimeError()
        directory = Path(tempfile.mkdtemp(prefix="scm-standalone-pg-", dir="/tmp"))
        directory.chmod(0o777)
        run = docker(["run", "--detach", "--rm", "--pull=never", "--name", name,
            "--label", "new-scm.test-purpose=4-2i", "--network=none", "--log-driver=none",
            "--memory=384m", "--cpus=1", "--pids-limit=128",
            "--mount", "type=bind,source=" + str(directory) + ",target=/var/run/postgresql",
            "--tmpfs", "/var/lib/postgresql/data:rw,size=256m",
            "--env", "POSTGRES_HOST_AUTH_METHOD=trust", "--env", "POSTGRES_DB=new_scm_dev", image])
        if run.returncode:
            # Only this random fixture name can be cleaned up, even on start failure.
            docker(["rm", "--force", name])
            raise RuntimeError()
        started = True
        for _ in range(80):
            if docker(["exec", name, "pg_isready", "-U", "postgres", "-d", "new_scm_dev"]).returncode == 0:
                break
            time.sleep(0.2)
        else:
            raise RuntimeError()
        runner = [sys.executable, "-B", str(Path(__file__).with_name("run_tests.py")),
                  "--compose-executable", str(Path(args.compose_executable).resolve(strict=True)),
                  "--postgres-socket", str(directory), "--postgres-container", name]
        if args.verifier_image:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.verifier_image):
                raise RuntimeError()
            runner += ["--verifier-image", args.verifier_image]
        code = subprocess.run(runner, env=environment).returncode
    except (Exception, KeyboardInterrupt):
        print("FAIL isolated_local_tests_unavailable_details_suppressed")
    finally:
        if started:
            try:
                removed = docker(["rm", "--force", name])
                if removed.returncode:
                    raise RuntimeError()
                removed_ok = True
                print("PASS isolated_local_postgres_removed")
            except Exception:
                print("FAIL isolated_local_postgres_cleanup")
                code = 1
        if directory is not None:
            try:
                if removed_ok:
                    # Force-removal leaves only these two PostgreSQL socket files
                    # in our temporary bind directory. No recursive deletion.
                    for path in directory.iterdir():
                        if (path.name == ".s.PGSQL.5432" and stat.S_ISSOCK(path.lstat().st_mode)
                                or path.name == ".s.PGSQL.5432.lock" and stat.S_ISREG(path.lstat().st_mode)):
                            path.unlink()
                directory.rmdir()
            except OSError:
                print("PENDING empty_fixture_directory_cleanup")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
