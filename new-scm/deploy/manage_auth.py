"""Python 3.12 operator terminal only; never prints or passes a password argument."""
import argparse
import os
from pathlib import Path
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    try:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--env-file", type=Path, required=True)
        parser.add_argument("--user-id", type=int, required=True)
        parser.add_argument("--initial-admin", action="store_true")
        args = parser.parse_args()
        if sys.version_info < (3, 12) or not sys.stdin.isatty():
            raise ValueError()
        path = args.env_file
        if path.is_symlink() or not path.is_file():
            raise ValueError()
        metadata = path.stat()
        if os.name == "posix" and (stat.S_IMODE(metadata.st_mode) != 0o600 or metadata.st_uid != os.geteuid()):
            raise ValueError()
        lines = path.read_text(encoding="utf-8").splitlines()
        for key in ("SCM_DATABASE_URL", "SCM_AUTH_DATABASE_URL"):
            values = [line.partition("=")[2] for line in lines if line.startswith(key + "=")]
            if len(values) != 1 or not values[0]:
                raise ValueError()
            # Load only the two target URLs; never source/execute a shell .env.
            os.environ[key] = values[0]
        os.environ.pop("SCM_DATABASE_SOCKET_DIR", None)
        sys.path.insert(0, str(ROOT / "backend"))
        from app.core.provision_auth import main as provision
        arguments = ["--user-id", str(args.user_id)]
        if args.initial_admin:
            arguments.append("--initial-admin")
        return provision(arguments)
    except (Exception, KeyboardInterrupt):
        print("FAIL scm_credentials_provisioning_failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
