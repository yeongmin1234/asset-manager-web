from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.department import Department


def get_active_categories(db: Session) -> List[Category]:
    statement = (
        select(Category)
        .where(Category.is_active.is_(True))
        .order_by(Category.sort_order.asc(), Category.id.asc())
    )
    return list(db.scalars(statement).all())


def get_active_departments(db: Session) -> List[Department]:
    statement = (
        select(Department)
        .where(Department.is_active.is_(True))
        .order_by(Department.sort_order.asc(), Department.id.asc())
    )
    return list(db.scalars(statement).all())
