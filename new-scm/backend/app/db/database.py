"""Read-only access to new_scm_dev only. No ORM metadata creation."""
from functools import lru_cache
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
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
    except (SQLAlchemyError, ValueError, TypeError):
        raise DatabaseUnavailable("database_configuration_invalid") from None
    if (url.drivername != "postgresql+psycopg" or url.database != EXPECTED_DATABASE
            or url.username != "new_scm_ro" or url.query):
        # Query parameters such as dbname/user/service can override URL fields.
        raise DatabaseUnavailable("database_target_rejected")
    return url


@lru_cache(maxsize=1)
def _engine():
    url = _validated_url(get_settings().database_url)
    socket_dir = os.getenv("SCM_DATABASE_SOCKET_DIR", "")
    if socket_dir:
        if socket_dir != "/srv/new-scm/db-socket":
            raise DatabaseUnavailable("database_socket_rejected")
        url = URL.create(url.drivername, username=url.username, password=url.password,
                         database=url.database, port=15432, query={"host": socket_dir})
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
