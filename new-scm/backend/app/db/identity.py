"""Read-only SCM identity repository. All grants come from the SCM database."""

from sqlalchemy import text
from sqlalchemy.engine import Connection


def load_identity(connection: Connection, issuer: str, subject: str):
    row = connection.execute(text("""
        SELECT u.id, u.name, u.account_type, u.status
        FROM public.scm_identity_mappings AS m
        JOIN public.users AS u ON u.id = m.user_id
        WHERE m.issuer = :issuer AND m.subject = :subject AND m.is_active = true
    """), {"issuer": issuer, "subject": subject}).one_or_none()
    if row is None or row.status != "active":
        return None
    grants = connection.execute(text("""
        SELECT grant_type, grant_name FROM public.scm_user_grants
        WHERE user_id = :user_id
    """), {"user_id": row.id}).all()
    return row, grants
