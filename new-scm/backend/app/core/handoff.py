"""Exchange an identity code, then resolve an explicit SCM subject mapping."""
from urllib.parse import urlparse

import httpx
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import Principal
from app.core.config import get_settings
from app.db.database import _engine


class HandoffRejected(Exception):
    pass


class MappingUnavailable(Exception):
    pass


def exchange_identity(code: str) -> tuple[str, str]:
    settings = get_settings()
    parsed = urlparse(settings.identity_base_url)
    if (not settings.handoff_key or len(settings.handoff_key) < 32
            or parsed.scheme not in {"https", "http"}
            or (parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"})
            or parsed.username or parsed.password or not parsed.hostname):
        raise HandoffRejected()
    try:
        with httpx.Client(timeout=3.0, follow_redirects=False, trust_env=False) as client:
            response = client.post(
                settings.identity_base_url + "/auth/scm-handoff/exchange",
                headers={"X-SCM-Handoff-Key": settings.handoff_key},
                json={"code": code, "audience": "new-scm"},
            )
        if response.status_code != 200:
            raise HandoffRejected()
        data = response.json()
        if (not isinstance(data, dict) or data.get("issuer") != "asset-manager"
                or data.get("audience") != "new-scm" or not str(data.get("subject", "")).isdigit()):
            raise HandoffRejected()
        return data["issuer"], data["subject"]
    except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
        raise HandoffRejected() from exc


def resolve_principal(issuer: str, subject: str) -> Principal | None:
    """Read proposed mapping/grant tables; absent schema safely denies access."""
    try:
        with _engine().connect() as connection:
            row = connection.execute(text("""
                SELECT u.id, u.name, u.account_type, u.status
                FROM scm_identity_mappings m JOIN users u ON u.id = m.user_id
                WHERE m.issuer = :issuer AND m.subject = :subject AND m.is_active = true
            """), {"issuer": issuer, "subject": subject}).one_or_none()
            if row is None or row.status != "active":
                return None
            grants = connection.execute(text("""
                SELECT grant_type, grant_name FROM scm_user_grants
                WHERE user_id = :user_id
            """), {"user_id": row.id}).all()
            connection.rollback()
        return Principal(
            subject=f"{issuer}:{subject}", name=row.name,
            account_type=row.account_type, status=row.status,
            menu_grants=frozenset(grant_name for grant_type, grant_name in grants if grant_type == "menu"),
            action_grants=frozenset(grant_name for grant_type, grant_name in grants if grant_type == "action"),
        )
    except (SQLAlchemyError, OSError, ValueError) as exc:
        raise MappingUnavailable() from exc
