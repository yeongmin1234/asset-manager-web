from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.company_vehicle import CompanyVehicle
from app.models.vehicle_insurance_history import VehicleInsuranceHistory
from app.schemas.vehicle_insurance_history import (
    VehicleInsuranceHistoryCreate,
    VehicleInsuranceHistoryRead,
    VehicleInsuranceHistoryUpdate,
)
from app.services.activity_log_service import (
    record_vehicle_insurance_history_activity,
    serialize_vehicle_insurance_history_activity_data,
)


class VehicleInsuranceHistoryNotFoundError(Exception):
    pass


class VehicleInsuranceHistoryVehicleNotFoundError(Exception):
    pass


def ensure_vehicle_exists(db: Session, vehicle_id: int) -> CompanyVehicle:
    vehicle = db.scalar(select(CompanyVehicle).where(CompanyVehicle.id == vehicle_id))
    if vehicle is None:
        raise VehicleInsuranceHistoryVehicleNotFoundError(f"Vehicle not found: {vehicle_id}")
    return vehicle


def get_vehicle_insurance_histories(
    db: Session,
    vehicle_id: int,
) -> List[VehicleInsuranceHistory]:
    ensure_vehicle_exists(db, vehicle_id)
    statement = (
        select(VehicleInsuranceHistory)
        .where(VehicleInsuranceHistory.vehicle_id == vehicle_id)
        .order_by(
            VehicleInsuranceHistory.start_date.desc().nullslast(),
            VehicleInsuranceHistory.id.desc(),
        )
    )
    return list(db.scalars(statement).all())


def create_vehicle_insurance_history(
    db: Session,
    vehicle_id: int,
    payload: VehicleInsuranceHistoryCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> VehicleInsuranceHistory:
    vehicle = ensure_vehicle_exists(db, vehicle_id)
    history = VehicleInsuranceHistory(vehicle_id=vehicle_id, **payload.model_dump())
    db.add(history)
    db.flush()
    record_vehicle_insurance_history_activity(
        db,
        action_type="등록",
        target_id=history.id,
        target_name=format_history_target_name(vehicle, history),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"보험 이력 등록: {format_history_target_name(vehicle, history)}",
        after_data=serialize_vehicle_insurance_history_activity_data(history),
    )
    db.commit()
    db.refresh(history)
    return history


def get_vehicle_insurance_history(db: Session, history_id: int) -> VehicleInsuranceHistory:
    history = db.scalar(
        select(VehicleInsuranceHistory).where(VehicleInsuranceHistory.id == history_id)
    )
    if history is None:
        raise VehicleInsuranceHistoryNotFoundError(
            f"Vehicle insurance history not found: {history_id}"
        )
    return history


def update_vehicle_insurance_history(
    db: Session,
    history_id: int,
    payload: VehicleInsuranceHistoryUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> VehicleInsuranceHistory:
    history = get_vehicle_insurance_history(db, history_id)
    vehicle = ensure_vehicle_exists(db, history.vehicle_id)
    before_data = serialize_vehicle_insurance_history_activity_data(history)
    for field_name, value in payload.model_dump().items():
        setattr(history, field_name, value)
    history.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_vehicle_insurance_history_activity(
        db,
        action_type="수정",
        target_id=history.id,
        target_name=format_history_target_name(vehicle, history),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"보험 이력 수정: {format_history_target_name(vehicle, history)}",
        before_data=before_data,
        after_data=serialize_vehicle_insurance_history_activity_data(history),
    )
    db.commit()
    db.refresh(history)
    return history


def delete_vehicle_insurance_history(
    db: Session,
    history_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> VehicleInsuranceHistoryRead:
    history = get_vehicle_insurance_history(db, history_id)
    vehicle = ensure_vehicle_exists(db, history.vehicle_id)
    before_data = serialize_vehicle_insurance_history_activity_data(history)
    target_name = format_history_target_name(vehicle, history)
    deleted_history = VehicleInsuranceHistoryRead.model_validate(history)
    record_vehicle_insurance_history_activity(
        db,
        action_type="삭제",
        target_id=history.id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"보험 이력 삭제: {target_name}",
        before_data=before_data,
    )
    db.delete(history)
    db.commit()
    return deleted_history


def format_history_target_name(
    vehicle: CompanyVehicle,
    history: VehicleInsuranceHistory,
) -> str:
    vehicle_label = vehicle.vehicle_number or vehicle.vehicle_name or f"차량 #{vehicle.id}"
    start_label = history.start_date.isoformat() if history.start_date else "-"
    end_label = history.end_date.isoformat() if history.end_date else "-"
    return f"{vehicle_label} / {start_label} ~ {end_label}"
