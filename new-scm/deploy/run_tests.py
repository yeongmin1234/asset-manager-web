"""Local test runner. Never creates a DB, migrates a NAS, or starts SCM services.

--postgres-socket enables tests against an EMPTY disposable /tmp local cluster.
--verifier-image explicitly enables one offline nonroot image smoke container.
"""
import argparse
import logging
import os
from pathlib import Path
import re
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-executable")
    parser.add_argument("--postgres-socket")
    parser.add_argument("--postgres-container", help="Verified disposable local cluster; enables custom backup/restore tests")
    parser.add_argument("--verifier-image")
    args = parser.parse_args()
    for key in list(os.environ):
        if key.startswith(("SCM_", "VITE_", "COMPOSE_", "DATABASE_")):
            os.environ.pop(key)
    if args.compose_executable:
        os.environ["SCM_TEST_COMPOSE"] = str(Path(args.compose_executable).resolve(strict=True))
    if args.postgres_socket:
        os.environ["SCM_TEST_PG_SOCKET"] = args.postgres_socket
    if args.postgres_container:
        if not args.postgres_socket or not re.fullmatch(r"scm-i-test-[0-9a-f]{32}", args.postgres_container):
            parser.error("local_fixture_container_required")
        os.environ["SCM_TEST_PG_CONTAINER"] = args.postgres_container
    if args.verifier_image:
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", args.verifier_image):
            parser.error("local_image_id_required")
        os.environ["SCM_TEST_PREFLIGHT_IMAGE"] = args.verifier_image
    root = Path(__file__).resolve().parents[1]
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(root / "backend"), str(root / "deploy")]
    logging.disable(logging.CRITICAL)
    suite = unittest.TestSuite()
    for folder in (root / "backend/tests", root / "deploy"):
        suite.addTests(unittest.TestLoader().discover(str(folder), top_level_dir=str(folder)))
    return 0 if unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
