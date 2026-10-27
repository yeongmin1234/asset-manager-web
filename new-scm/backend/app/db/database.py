"""Read-only access to new_scm_dev only. No ORM metadata creation."""
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings


EXPECTED_DATABASE = "new_scm_dev"


class DatabaseUnavailable(Exception):
    pass


def _validated_url(raw_url: str):
    if not raw_url:
        raise DatabaseUnavailable("database_not_configured")
    try:
        url = make_url(raw_url)
    except (ValueError, TypeError):
        raise DatabaseUnavailable("database_configuration_invalid") from None
    if url.get_backend_name() != "postgresql" or url.database != EXPECTED_DATABASE:
        raise DatabaseUnavailable("database_target_rejected")
    return url


@lru_cache(maxsize=1)
def _engine():
    url = _validated_url(get_settings().database_url)
    return create_engine(
        url,
        pool_size=2,
        max_overflow=0,
        pool_timeout=3,
        pool_pre_ping=True,
        connect_args={
            "connect_timeout": 3,
            "options": "-c default_transaction_read_only=on -c statement_timeout=3000",
        },
    )


def probe_database() -> dict:
    try:
        with _engine().connect() as connection:
            row = connection.execute(
                text("SELECT current_database(), current_setting('transaction_read_only')")
            ).one()
            if row[0] != EXPECTED_DATABASE or row[1] != "on":
                raise DatabaseUnavailable("read_only_verification_failed")
            count = connection.execute(
                text("SELECT count(*) FROM information_schema.tables "
                     "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")
            ).scalar_one()
            connection.rollback()
            return {"connected": True, "read_only": True, "table_count": count}
    except DatabaseUnavailable:
        raise
    except (SQLAlchemyError, OSError, ValueError):
        raise DatabaseUnavailable("database_probe_failed") from None
