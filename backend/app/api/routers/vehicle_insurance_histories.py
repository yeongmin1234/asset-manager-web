from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.user import User
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
    get_vehicle_insurance_history,
    update_vehicle_insurance_history,
)
from app.services.audit_log_service import audit_snapshot, build_audit_changes, record_audit_log


router = APIRouter(tags=["vehicle-insurance-histories"])
INSURANCE_AUDIT_FIELDS = ("vehicle_id", "start_date", "end_date", "insurance_type", "driver_name", "amount", "payment_method", "note")


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
    current_user: User = Depends(get_current_user),
) -> VehicleInsuranceHistoryRead:
    try:
        result = create_vehicle_insurance_history(
            db,
            vehicle_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="create", menu_key="company_cars", menu_name="법인차량 관리", target_type="vehicle_insurance_history", target_id=result.id, target_name="차량 보험 이력 #{}".format(result.id), action_summary="차량 보험 이력을 등록했습니다.", after_data=audit_snapshot(result, INSURANCE_AUDIT_FIELDS))
        return result
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
    current_user: User = Depends(get_current_user),
) -> VehicleInsuranceHistoryRead:
    try:
        before = audit_snapshot(get_vehicle_insurance_history(db, history_id), INSURANCE_AUDIT_FIELDS)
        result = update_vehicle_insurance_history(
            db,
            history_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        before_changed, after_changed, changed = build_audit_changes(before, audit_snapshot(result, INSURANCE_AUDIT_FIELDS))
        record_audit_log(db, request, current_user, action_type="update", menu_key="company_cars", menu_name="법인차량 관리", target_type="vehicle_insurance_history", target_id=result.id, target_name="차량 보험 이력 #{}".format(result.id), action_summary="차량 보험 이력을 수정했습니다.", before_data=before_changed, after_data=after_changed, changed_fields=changed)
        return result
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
    current_user: User = Depends(get_current_user),
) -> VehicleInsuranceHistoryRead:
    try:
        before = audit_snapshot(get_vehicle_insurance_history(db, history_id), INSURANCE_AUDIT_FIELDS)
        result = delete_vehicle_insurance_history(
            db,
            history_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        record_audit_log(db, request, current_user, action_type="delete", menu_key="company_cars", menu_name="법인차량 관리", target_type="vehicle_insurance_history", target_id=result.id, target_name="차량 보험 이력 #{}".format(result.id), action_summary="차량 보험 이력을 삭제했습니다.", before_data=before)
        return result
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
