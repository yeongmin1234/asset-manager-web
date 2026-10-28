"""New SCM migrations only. No URL is read from the application's RO setting."""
import os
import stat
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def migration_url():
    raw = os.getenv("SCM_MIGRATION_DATABASE_URL", "")
    expected_role = os.getenv("SCM_MIGRATION_ROLE", "")
    backup = Path(os.getenv("SCM_MIGRATION_BACKUP_PATH", ""))
    if not raw or not expected_role or expected_role in {"new_scm_ro", "new_scm_reader", "new_scm_auth"}:
        raise RuntimeError("Dedicated SCM migration credentials are required")
    try:
        url = make_url(raw)
    except Exception:
        raise RuntimeError("SCM migration URL invalid") from None
    if (url.drivername != "postgresql+psycopg" or url.query or url.host != "127.0.0.1"
            or url.port != 5432 or url.database != "new_scm_dev"
            or url.username != expected_role):
        raise RuntimeError("SCM migration target or role rejected")
    if not backup.is_absolute() or backup.is_symlink() or not backup.is_file() or backup.stat().st_size == 0:
        raise RuntimeError("Verified SCM backup artifact is required")
    if os.name == "posix" and (stat.S_IMODE(backup.stat().st_mode) != 0o600 or backup.stat().st_uid != os.geteuid()):
        raise RuntimeError("SCM backup owner and mode 600 required")
    with backup.open("rb") as artifact:
        if artifact.read(5) != b"PGDMP":
            raise RuntimeError("A PostgreSQL custom-format backup is required")
    return url, expected_role


if context.is_offline_mode():
    raise RuntimeError("Offline SCM migration is disabled")

url, role = migration_url()
engine = create_engine(url, hide_parameters=True,
                       connect_args={"connect_timeout": 3, "options": "-c statement_timeout=15000"})
with engine.connect() as connection:
    database, current_role, readonly = connection.execute(text(
        "SELECT current_database(), current_user, current_setting('transaction_read_only')"
    )).one()
    if (database, current_role, readonly) != ("new_scm_dev", role, "off"):
        raise RuntimeError("SCM migration connection preflight failed")
    connection.rollback()
    context.configure(connection=connection, target_metadata=None, transactional_ddl=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()

