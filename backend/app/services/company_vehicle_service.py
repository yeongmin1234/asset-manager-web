from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.company_vehicle import CompanyVehicle, VehicleOwnershipType
from app.models.attachment import AttachmentEntityType
from app.schemas.company_vehicle import (
    CompanyVehicleCreate,
    CompanyVehicleRead,
    CompanyVehicleSummary,
    CompanyVehicleUpdate,
)
from app.services.activity_log_service import (
    record_vehicle_activity,
    serialize_vehicle_activity_data,
)
from app.services.attachment_service import ensure_no_attachments


class CompanyVehicleNotFoundError(Exception):
    pass


def get_company_vehicles(
    db: Session,
    *,
    ownership_type: Optional[VehicleOwnershipType] = None,
) -> List[CompanyVehicle]:
    statement = select(CompanyVehicle)
    if ownership_type is not None:
        statement = statement.where(CompanyVehicle.ownership_type == ownership_type)
    statement = statement.order_by(CompanyVehicle.created_at.desc(), CompanyVehicle.id.desc())
    return list(db.scalars(statement).all())


def create_company_vehicle(
    db: Session,
    payload: CompanyVehicleCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> CompanyVehicle:
    vehicle = CompanyVehicle(**payload.model_dump())
    db.add(vehicle)
    db.flush()
    record_vehicle_activity(
        db,
        action_type="create",
        target_id=vehicle.id,
        target_name=format_vehicle_target_name(vehicle),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"차량 등록: {format_vehicle_target_name(vehicle)}",
        after_data=serialize_vehicle_activity_data(vehicle),
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle


def get_company_vehicle(db: Session, vehicle_id: int) -> CompanyVehicle:
    vehicle = db.scalar(select(CompanyVehicle).where(CompanyVehicle.id == vehicle_id))
    if vehicle is None:
        raise CompanyVehicleNotFoundError(f"Company vehicle not found: {vehicle_id}")
    return vehicle


def update_company_vehicle(
    db: Session,
    vehicle_id: int,
    payload: CompanyVehicleUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> CompanyVehicle:
    vehicle = get_company_vehicle(db, vehicle_id)
    before_data = serialize_vehicle_activity_data(vehicle)
    for field_name, value in payload.model_dump().items():
        setattr(vehicle, field_name, value)
    vehicle.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_vehicle_activity(
        db,
        action_type="update",
        target_id=vehicle.id,
        target_name=format_vehicle_target_name(vehicle),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"차량 수정: {format_vehicle_target_name(vehicle)}",
        before_data=before_data,
        after_data=serialize_vehicle_activity_data(vehicle),
    )
    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_company_vehicle(
    db: Session,
    vehicle_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> CompanyVehicleRead:
    vehicle = get_company_vehicle(db, vehicle_id)
    ensure_no_attachments(db, AttachmentEntityType.COMPANY_CAR, vehicle_id)
    before_data = serialize_vehicle_activity_data(vehicle)
    target_name = format_vehicle_target_name(vehicle)
    deleted_vehicle = CompanyVehicleRead.model_validate(vehicle)
    record_vehicle_activity(
        db,
        action_type="delete",
        target_id=vehicle.id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"차량 삭제: {target_name}",
        before_data=before_data,
    )
    db.delete(vehicle)
    db.commit()
    return deleted_vehicle


def get_company_vehicle_summary(db: Session) -> CompanyVehicleSummary:
    today = date.today()
    insurance_deadline = today + timedelta(days=30)
    lease_deadline = today + timedelta(days=60)

    expiring_condition = or_(
        CompanyVehicle.insurance_end_date.between(today, insurance_deadline),
        CompanyVehicle.lease_end_date.between(today, lease_deadline),
    )

    row = db.execute(
        select(
            func.count(CompanyVehicle.id).label("total_vehicles"),
            func.coalesce(
                func.sum(
                    case(
                        (CompanyVehicle.ownership_type == VehicleOwnershipType.COMPANY, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("company_owned_count"),
            func.coalesce(
                func.sum(
                    case(
                        (CompanyVehicle.ownership_type == VehicleOwnershipType.LEASE, 1),
                        else_=0,
                    )
                ),
                0,
            ).label("lease_count"),
            func.coalesce(
                func.sum(case((expiring_condition, 1), else_=0)),
                0,
            ).label("expiring_soon_count"),
        )
    ).one()

    return CompanyVehicleSummary(
        total_vehicles=int(row.total_vehicles or 0),
        company_owned_count=int(row.company_owned_count or 0),
        lease_count=int(row.lease_count or 0),
        expiring_soon_count=int(row.expiring_soon_count or 0),
    )


def format_vehicle_target_name(vehicle: CompanyVehicle) -> str:
    parts = [vehicle.vehicle_number, vehicle.vehicle_name]
    return " / ".join(part for part in parts if part) or f"차량 #{vehicle.id}"
