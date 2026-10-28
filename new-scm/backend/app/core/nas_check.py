"""Fixed-output read-only probes for an approved, already-running test backend."""
import argparse
import os
from pathlib import Path
import stat


def check_socket():
    from app.db import relay
    path = Path(relay.SOCKET_PATH)
    directory, endpoint = path.parent.stat(), path.stat()
    if (os.geteuid(), os.getegid()) != (10001, 10001):
        raise ValueError()
    if (directory.st_uid, directory.st_gid, stat.S_IMODE(directory.st_mode)) != (10001, 10001, 0o700):
        raise ValueError()
    if (not stat.S_ISSOCK(endpoint.st_mode)
            or (endpoint.st_uid, endpoint.st_gid, stat.S_IMODE(endpoint.st_mode)) != (10001, 10001, 0o700)):
        raise ValueError()
    relay.check()  # SSLRequest only, through the backend's read-only socket mount.


def check_database():
    from app.db.database import probe_database
    result = probe_database()
    if result != {"connected": True, "read_only": True, "table_count": 54}:
        raise ValueError()


def check_auth():
    from app.db.local_auth import engine
    from app.db.auth_policy import verify_auth_connection
    from sqlalchemy import text
    with engine().connect() as db:
        db.execute(text("SET TRANSACTION READ ONLY"))
        verify_auth_connection(db)
        db.rollback()


def check_health():
    import httpx
    with httpx.Client(timeout=3, trust_env=False, follow_redirects=False) as client:
        for path in ("/health", "/api/v1/system/status"):
            response = client.get("http://127.0.0.1:8012" + path)
            if response.status_code != 200 or response.json().get("ok") is not True:
                raise ValueError()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=("socket", "database", "auth", "health"))
    args = parser.parse_args(argv)
    checks = {"socket": check_socket, "database": check_database,
              "auth": check_auth, "health": check_health}
    try:
        checks[args.check]()
        print("PASS nas_test_" + args.check)
        return 0
    except Exception:
        print("FAIL nas_test_" + args.check)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
