"""Short-lived process-local SCM sessions. Never stores the original JWT."""
from hashlib import sha256
from secrets import token_urlsafe
from threading import Lock
from time import monotonic

_sessions: dict[str, tuple[str, str, float]] = {}
_lock = Lock()
SESSION_SECONDS = 1800


def create(issuer: str, subject: str) -> str:
    token = token_urlsafe(48)
    now = monotonic()
    with _lock:
        for digest, (_, _, expires) in list(_sessions.items()):
            if expires <= now:
                del _sessions[digest]
        _sessions[sha256(token.encode()).hexdigest()] = (issuer, subject, now + SESSION_SECONDS)
    return token


def lookup(token: str) -> tuple[str, str] | None:
    with _lock:
        entry = _sessions.get(sha256(token.encode()).hexdigest())
        if entry is None:
            return None
        if entry[2] <= monotonic():
            del _sessions[sha256(token.encode()).hexdigest()]
            return None
        return entry[0], entry[1]


def revoke(token: str) -> None:
    with _lock:
        _sessions.pop(sha256(token.encode()).hexdigest(), None)
