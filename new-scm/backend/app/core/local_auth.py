"""Standalone SCM passwords and persistent, revocable opaque sessions.

Only fixed event codes enter logs. Tokens/passwords/usernames/peer addresses do not.
Public users/password_hash and legacy mappings are never written here.
"""
from contextlib import contextmanager
from hashlib import sha256
import logging
import secrets
from threading import BoundedSemaphore
import time
import unicodedata

from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from sqlalchemy import text

from app.db.local_auth import engine, principal_for

SESSION_SECONDS = 1800
WINDOW_SECONDS = 900
hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1, type=Type.ID)
_dummy_hash = hasher.hash(secrets.token_urlsafe(32))
_hash_slots = BoundedSemaphore(2)
logger = logging.getLogger("new_scm.auth")


class AuthFailure(Exception):
    def __init__(self, code, status=401):
        self.code, self.status = code, status


def digest(value):
    return sha256(value.encode("utf-8")).hexdigest()


def password_policy(password):
    # Length only: allow passphrases and Unicode, never truncate silently.
    return isinstance(password, str) and 12 <= len(password) <= 256


@contextmanager
def hashing_slot():
    if not _hash_slots.acquire(blocking=False):
        raise AuthFailure("auth_busy", 503)
    try:
        yield
    finally:
        _hash_slots.release()


def hash_password(password):
    if not password_policy(password):
        raise AuthFailure("password_policy_invalid", 422)
    with hashing_slot():
        return hasher.hash(password)


def _consume_attempt(username, peer, now):
    # PostgreSQL's atomic upsert serializes concurrent attempts, across workers.
    # Attempt counters commit even when credentials fail. Never reset on success.
    bucket = now // WINDOW_SECONDS
    normalized = unicodedata.normalize("NFKC", username).casefold()
    # Stop allocating account buckets when a peer is already blocked.
    keys = (("peer:" + digest(peer), 50), ("account:" + digest(normalized), 5))
    exceeded = False
    with engine().begin() as db:
        db.execute(text("DELETE FROM scm_auth.login_limits WHERE expires_at < :now"), {"now": now})
        for key, maximum in keys:
            count = db.execute(text("""
                INSERT INTO scm_auth.login_limits (bucket_key, window_id, attempts, expires_at)
                VALUES (:key, :window, 1, :expiry)
                ON CONFLICT (bucket_key, window_id) DO UPDATE
                SET attempts = scm_auth.login_limits.attempts + 1
                RETURNING attempts
            """), {"key": key, "window": bucket, "expiry": (bucket + 2) * WINDOW_SECONDS}).scalar_one()
            exceeded = exceeded or count > maximum
            if exceeded:
                break
    if exceeded:
        logger.warning("auth_login_throttled")
        raise AuthFailure("login_rate_limited", 429)


def login(username, password, peer, previous_token=""):
    now = int(time.time())
    _consume_attempt(username, peer, now)
    with engine().connect() as db:
        row = db.execute(text("""
            SELECT c.user_id, c.password_hash, c.enabled FROM scm_auth.credentials c
            JOIN public.users u ON u.id=c.user_id WHERE u.username=:username
        """), {"username": username}).mappings().first()
    encoded = row["password_hash"] if row is not None else _dummy_hash
    with hashing_slot():
        try:
            valid = hasher.verify(encoded, password)
        except (VerificationError, InvalidHashError):
            valid = False
    if not valid or row is None or not row["enabled"]:
        logger.warning("auth_login_rejected")
        raise AuthFailure("invalid_credentials")
    token = secrets.token_urlsafe(48)
    with engine().begin() as db:
        # Lock credentials so a concurrent reset/disable cannot leave a new session.
        current = db.execute(text("SELECT password_hash, enabled FROM scm_auth.credentials "
                                  "WHERE user_id=:id FOR UPDATE"), {"id": row["user_id"]}).mappings().first()
        principal = principal_for(db, row["user_id"])
        if (current is None or not current["enabled"] or current["password_hash"] != encoded
                or principal is None or "system.access" not in principal.action_grants):
            logger.warning("auth_login_rejected")
            raise AuthFailure("invalid_credentials")
        if hasher.check_needs_rehash(encoded):
            encoded = hash_password(password)
            db.execute(text("UPDATE scm_auth.credentials SET password_hash=:hash, updated_at=:now WHERE user_id=:id"),
                       {"hash": encoded, "now": now, "id": row["user_id"]})
        db.execute(text("DELETE FROM scm_auth.sessions WHERE expires_at<=:now OR token_hash=:old"),
                   {"now": now, "old": digest(previous_token)})
        db.execute(text("INSERT INTO scm_auth.sessions (token_hash,user_id,created_at,expires_at) "
                        "VALUES (:hash,:id,:now,:expiry)"),
                   {"hash": digest(token), "id": row["user_id"], "now": now, "expiry": now + SESSION_SECONDS})
    logger.info("auth_login_succeeded")
    return token


def lookup(token):
    if not isinstance(token, str) or len(token) != 64:
        return None
    with engine().connect() as db:
        user_id = db.execute(text("""
            SELECT s.user_id FROM scm_auth.sessions s
            JOIN scm_auth.credentials c ON c.user_id=s.user_id
            WHERE s.token_hash=:hash AND s.expires_at>:now AND c.enabled
        """), {"hash": digest(token), "now": int(time.time())}).scalar_one_or_none()
        return principal_for(db, user_id) if user_id is not None else None


def logout(token):
    with engine().begin() as db:
        db.execute(text("DELETE FROM scm_auth.sessions WHERE token_hash=:hash"), {"hash": digest(token)})
    logger.info("auth_logout_succeeded")


def list_users():
    with engine().connect() as db:
        return [dict(row) for row in db.execute(text("""
            SELECT u.id, u.username, u.name, u.account_type, u.status,
                   COALESCE(c.enabled, false) AS login_enabled,
                   (c.user_id IS NOT NULL) AS credentials_configured
            FROM public.users u LEFT JOIN scm_auth.credentials c ON c.user_id=u.id ORDER BY u.id
        """)).mappings()]


def set_credentials(user_id, password, enabled):
    encoded = hash_password(password) if password is not None else None
    with engine().begin() as db:
        if principal_for(db, user_id) is None:
            raise AuthFailure("user_unavailable", 404)
        if encoded is not None:
            db.execute(text("""
                INSERT INTO scm_auth.credentials (user_id,password_hash,enabled,updated_at)
                VALUES (:id,:hash,:enabled,:now) ON CONFLICT (user_id) DO UPDATE
                SET password_hash=excluded.password_hash,enabled=excluded.enabled,updated_at=excluded.updated_at
            """), {"id": user_id, "hash": encoded, "enabled": enabled, "now": int(time.time())})
        else:
            result = db.execute(text("UPDATE scm_auth.credentials SET enabled=:enabled WHERE user_id=:id"),
                                {"enabled": enabled, "id": user_id})
            if result.rowcount != 1:
                raise AuthFailure("credentials_not_configured", 409)
        db.execute(text("DELETE FROM scm_auth.sessions WHERE user_id=:id"), {"id": user_id})
    logger.info("auth_credentials_changed")
