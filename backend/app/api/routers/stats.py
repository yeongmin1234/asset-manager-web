from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.stats import (
    AssetStatsSummary,
    CategoryAssetStats,
    DepartmentAssetStats,
    MonthlyAssetStats,
)
from app.services.stats_service import (
    get_asset_stats_by_category,
    get_asset_stats_by_department,
    get_asset_stats_monthly,
    get_asset_stats_summary,
)


router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=AssetStatsSummary)
def read_stats_summary(db: Session = Depends(get_db)) -> AssetStatsSummary:
    try:
        return get_asset_stats_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading asset stats.",
        ) from exc


@router.get("/by-category", response_model=list[CategoryAssetStats])
def read_stats_by_category(db: Session = Depends(get_db)) -> list[CategoryAssetStats]:
    try:
        return get_asset_stats_by_category(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading category asset stats.",
        ) from exc


@router.get("/by-department", response_model=list[DepartmentAssetStats])
def read_stats_by_department(
    db: Session = Depends(get_db),
) -> list[DepartmentAssetStats]:
    try:
        return get_asset_stats_by_department(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading department asset stats.",
        ) from exc


@router.get("/monthly", response_model=list[MonthlyAssetStats])
def read_stats_monthly(db: Session = Depends(get_db)) -> list[MonthlyAssetStats]:
    try:
        return get_asset_stats_monthly(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading monthly asset stats.",
        ) from exc
