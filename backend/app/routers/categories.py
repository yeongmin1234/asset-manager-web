from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryRead, CategoryLookup
from app.services.lookup_service import get_active_categories


router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryLookup])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryLookup]:
    try:
        return get_active_categories(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading categories.",
        ) from exc


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> Category:
    name = payload.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="분류명을 입력해주세요.",
        )

    existing = db.query(Category).filter(func.lower(Category.name) == name.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 분류명입니다.",
        )

    category = Category(
        name=name,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(category)
    try:
        db.commit()
        db.refresh(category)
        return category
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 존재하는 분류명입니다.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating category.",
        ) from exc
