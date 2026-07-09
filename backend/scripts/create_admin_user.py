import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import select


BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.auth import hash_password  # noqa: E402
from app.db.database import SessionLocal  # noqa: E402
from app.models.user import User  # noqa: E402


def main() -> int:
    username = (os.getenv("ADMIN_USERNAME") or input("Username: ")).strip()
    name = (os.getenv("ADMIN_NAME") or input("Name: ")).strip()
    password = os.getenv("ADMIN_PASSWORD") or getpass.getpass("Password: ")
    if not username or not name or len(password) < 8:
        print("Username/name are required and password must be at least 8 characters.")
        return 1

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.username == username)) is not None:
            print("User already exists; no user was created.")
            return 1
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                name=name,
                role="admin",
                is_active=True,
            )
        )
        db.commit()
    print("Admin user created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
