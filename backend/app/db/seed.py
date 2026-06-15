from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.db.database import SessionLocal
from app.db.seed_data import DEFAULT_CATEGORIES, DEFAULT_DEPARTMENTS
import app.models  # noqa: F401
from app.models.category import Category
from app.models.department import Department


def ensure_development_environment() -> None:
    if settings.app_env.lower() == "production":
        raise RuntimeError("Refusing to run seed command when APP_ENV=production.")


def seed_categories() -> int:
    created_count = 0

    with SessionLocal() as db:
        for item in DEFAULT_CATEGORIES:
            existing = db.scalar(
                select(Category).where(Category.name == item["name"])
            )
            if existing is not None:
                continue

            db.add(
                Category(
                    name=item["name"],
                    sort_order=item["sort_order"],
                    is_active=True,
                )
            )
            created_count += 1

        db.commit()

    return created_count


def seed_departments() -> int:
    created_count = 0

    with SessionLocal() as db:
        for item in DEFAULT_DEPARTMENTS:
            existing = db.scalar(
                select(Department).where(Department.name == item["name"])
            )
            if existing is not None:
                continue

            db.add(
                Department(
                    name=item["name"],
                    sort_order=item["sort_order"],
                    is_active=True,
                )
            )
            created_count += 1

        db.commit()

    return created_count


def main() -> None:
    try:
        ensure_development_environment()
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        category_count = seed_categories()
        department_count = seed_departments()
    except SQLAlchemyError as exc:
        raise SystemExit(f"Seed failed: {exc}") from exc

    print(
        "Seed complete. "
        f"Created categories: {category_count}, "
        f"departments: {department_count}"
    )


if __name__ == "__main__":
    main()
