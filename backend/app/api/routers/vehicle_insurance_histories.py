from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.vehicle_insurance_history import (
    VehicleInsuranceHistoryCreate,
    VehicleInsuranceHistoryRead,
    VehicleInsuranceHistoryUpdate,
)
from app.services.vehicle_insurance_history_service import (
    VehicleInsuranceHistoryNotFoundError,
    VehicleInsuranceHistoryVehicleNotFoundError,
    create_vehicle_insurance_history,
    delete_vehicle_insurance_history,
    get_vehicle_insurance_histories,
    update_vehicle_insurance_history,
)


router = APIRouter(tags=["vehicle-insurance-histories"])


@router.get(
    "/vehicles/{vehicle_id}/insurance-histories",
    response_model=List[VehicleInsuranceHistoryRead],
)
def list_vehicle_insurance_histories(
    vehicle_id: int,
    db: Session = Depends(get_db),
) -> List[VehicleInsuranceHistoryRead]:
    try:
        return get_vehicle_insurance_histories(db, vehicle_id)
    except VehicleInsuranceHistoryVehicleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        ) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading insurance histories.",
        ) from exc


@router.post(
    "/vehicles/{vehicle_id}/insurance-histories",
    response_model=VehicleInsuranceHistoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_new_vehicle_insurance_history(
    request: Request,
    vehicle_id: int,
    payload: VehicleInsuranceHistoryCreate,
    db: Session = Depends(get_db),
) -> VehicleInsuranceHistoryRead:
    try:
        return create_vehicle_insurance_history(
            db,
            vehicle_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except VehicleInsuranceHistoryVehicleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating insurance history.",
        ) from exc


@router.put(
    "/vehicles/insurance-histories/{history_id}",
    response_model=VehicleInsuranceHistoryRead,
)
def update_existing_vehicle_insurance_history(
    request: Request,
    history_id: int,
    payload: VehicleInsuranceHistoryUpdate,
    db: Session = Depends(get_db),
) -> VehicleInsuranceHistoryRead:
    try:
        return update_vehicle_insurance_history(
            db,
            history_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except VehicleInsuranceHistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance history not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating insurance history.",
        ) from exc


@router.delete(
    "/vehicles/insurance-histories/{history_id}",
    response_model=VehicleInsuranceHistoryRead,
)
def delete_existing_vehicle_insurance_history(
    request: Request,
    history_id: int,
    db: Session = Depends(get_db),
) -> VehicleInsuranceHistoryRead:
    try:
        return delete_vehicle_insurance_history(
            db,
            history_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except VehicleInsuranceHistoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insurance history not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting insurance history.",
        ) from exc
