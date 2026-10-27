"""New SCM migrations only. No URL is read from the application's RO setting."""
import os
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def migration_url():
    raw = os.getenv("SCM_MIGRATION_DATABASE_URL", "")
    expected_role = os.getenv("SCM_MIGRATION_ROLE", "")
    backup = Path(os.getenv("SCM_MIGRATION_BACKUP_PATH", ""))
    if not raw or not expected_role or expected_role in {"new_scm_ro", "new_scm_reader"}:
        raise RuntimeError("Dedicated SCM migration credentials are required")
    url = make_url(raw)
    if (url.get_backend_name() != "postgresql" or url.host != "127.0.0.1"
            or url.port != 5432 or url.database != "new_scm_dev"
            or url.username != expected_role):
        raise RuntimeError("SCM migration target or role rejected")
    if not backup.is_absolute() or not backup.is_file() or backup.stat().st_size == 0:
        raise RuntimeError("Verified SCM backup artifact is required")
    with backup.open("rb") as artifact:
        if artifact.read(5) != b"PGDMP":
            raise RuntimeError("A PostgreSQL custom-format backup is required")
    return url, expected_role


if context.is_offline_mode():
    raise RuntimeError("Offline SCM migration is disabled")

url, role = migration_url()
engine = create_engine(url, connect_args={"connect_timeout": 3, "options": "-c statement_timeout=15000"})
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

