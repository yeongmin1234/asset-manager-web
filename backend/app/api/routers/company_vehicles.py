from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.models.company_vehicle import VehicleOwnershipType
from app.schemas.company_vehicle import (
    CompanyVehicleCreate,
    CompanyVehicleRead,
    CompanyVehicleSummary,
    CompanyVehicleUpdate,
)
from app.services.company_vehicle_service import (
    CompanyVehicleNotFoundError,
    create_company_vehicle,
    delete_company_vehicle,
    get_company_vehicle_summary,
    get_company_vehicles,
    update_company_vehicle,
)
from app.services.attachment_service import AttachmentValidationError


router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=List[CompanyVehicleRead])
def list_company_vehicles(
    ownership_type: Optional[VehicleOwnershipType] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CompanyVehicleRead]:
    try:
        return get_company_vehicles(db, ownership_type=ownership_type)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading vehicles.",
        ) from exc


@router.post("", response_model=CompanyVehicleRead, status_code=status.HTTP_201_CREATED)
def create_new_company_vehicle(
    request: Request,
    payload: CompanyVehicleCreate,
    db: Session = Depends(get_db),
) -> CompanyVehicleRead:
    try:
        result = create_company_vehicle(
            db,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="company_cars", menu_name="법인차량 관리", target_type="company_vehicle", target_id=result.id, target_name=result.vehicle_number, action_summary="법인차량을 등록했습니다.")
        return result
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating vehicle.",
        ) from exc


@router.put("/{vehicle_id}", response_model=CompanyVehicleRead)
def update_existing_company_vehicle(
    request: Request,
    vehicle_id: int,
    payload: CompanyVehicleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyVehicleRead:
    try:
        result = update_company_vehicle(
            db,
            vehicle_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="update", menu_key="company_cars", menu_name="법인차량 관리", target_type="company_vehicle", target_id=result.id, target_name=result.vehicle_number, action_summary="법인차량을 수정했습니다.")
        return result
    except CompanyVehicleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating vehicle.",
        ) from exc


@router.delete("/{vehicle_id}", response_model=CompanyVehicleRead)
def delete_existing_company_vehicle(
    request: Request,
    vehicle_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyVehicleRead:
    try:
        result = delete_company_vehicle(
            db,
            vehicle_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="delete", menu_key="company_cars", menu_name="법인차량 관리", target_type="company_vehicle", target_id=result.id, target_name=result.vehicle_number, action_summary="법인차량을 삭제했습니다.")
        return result
    except CompanyVehicleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found.",
        ) from exc
    except AttachmentValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting vehicle.",
        ) from exc


@router.get("/summary", response_model=CompanyVehicleSummary)
def read_company_vehicle_summary(
    db: Session = Depends(get_db),
) -> CompanyVehicleSummary:
    try:
        return get_company_vehicle_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading vehicle summary.",
        ) from exc
