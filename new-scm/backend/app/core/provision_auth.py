"""Interactive credential setup for explicitly selected, already-approved SCM users.

Run on a trusted operator terminal with the dedicated auth DB URL in the environment.
No password argument, generated password, default user ID, or role/grant assignment.
"""
import argparse
from getpass import getpass
import sys

from app.core.local_auth import set_credentials
from app.db.local_auth import engine, principal_for


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-id", required=True, type=int)
    parser.add_argument("--initial-admin", action="store_true")
    args = parser.parse_args(argv)
    try:
        if not sys.stdin.isatty() or args.user_id <= 0:
            raise ValueError()
        with engine().connect() as db:
            user = principal_for(db, args.user_id)
            if user is None or "system.access" not in user.action_grants:
                raise ValueError()
            if args.initial_admin and (user.account_type != "admin" or "admin.manage" not in user.action_grants):
                raise ValueError()
        password = getpass("SCM password (12–256 characters): ")
        confirmation = getpass("Confirm SCM password: ")
        if password != confirmation:
            raise ValueError()
        set_credentials(args.user_id, password, True)
        print("PASS scm_credentials_provisioned_sessions_revoked")
        return 0
    except (Exception, KeyboardInterrupt):
        print("FAIL scm_credentials_provisioning_failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
