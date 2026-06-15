from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.category import CategoryLookup
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
