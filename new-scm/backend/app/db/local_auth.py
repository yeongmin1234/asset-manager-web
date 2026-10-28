"""Dedicated authentication connection; never used for business data writes."""
from functools import lru_cache
import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from app.core.config import get_settings


class AuthUnavailable(Exception):
    pass


def validated_url(raw):
    try:
        url = make_url(raw)
        if (url.drivername != "postgresql+psycopg" or url.database != "new_scm_dev"
                or url.username != "new_scm_auth" or not url.password or url.query):
            raise ValueError()
        return url
    except Exception:
        raise AuthUnavailable("auth_database_target_rejected") from None


@lru_cache(maxsize=1)
def engine():
    settings = get_settings()
    url = validated_url(settings.auth_database_url)
    from app.db.database import _validated_url
    reader = _validated_url(settings.database_url)
    if (reader.host, reader.port) != (url.host, url.port):
        raise AuthUnavailable("auth_and_reader_targets_differ")
    socket = os.getenv("SCM_DATABASE_SOCKET_DIR", "")
    if socket:
        if socket != "/srv/new-scm/db-socket":
            raise AuthUnavailable("auth_database_socket_rejected")
        url = URL.create(url.drivername, username=url.username, password=url.password,
                         database=url.database, port=15432, query={"host": socket})
    return create_engine(url, pool_size=2, max_overflow=0, pool_timeout=3,
                         pool_pre_ping=True, hide_parameters=True,
                         connect_args={"connect_timeout": 3,
                                       "options": "-c statement_timeout=3000 -c lock_timeout=2000"})


def principal_for(db, user_id):
    from app.core.auth import Principal
    row = db.execute(text("SELECT id, name, account_type, status FROM public.users WHERE id=:id"),
                     {"id": user_id}).mappings().first()
    if row is None or row["status"] != "active":
        return None
    grants = db.execute(text("SELECT grant_type, grant_name FROM public.scm_user_grants WHERE user_id=:id"),
                        {"id": user_id}).all()
    return Principal(str(row["id"]), row["name"], row["account_type"], row["status"],
                     frozenset(name for kind, name in grants if kind == "menu"),
                     frozenset(name for kind, name in grants if kind == "action"))
