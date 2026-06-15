from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.department import DepartmentLookup
from app.services.lookup_service import get_active_departments


router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=List[DepartmentLookup])
def list_departments(db: Session = Depends(get_db)) -> List[DepartmentLookup]:
    try:
        return get_active_departments(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading departments.",
        ) from exc
