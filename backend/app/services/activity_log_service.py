from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity_log import SystemActivityLog
from app.models.asset import Asset
from app.models.company_vehicle import CompanyVehicle
from app.models.software_item import SoftwareItem
from app.models.vehicle_insurance_history import VehicleInsuranceHistory


SOFTWARE_LOG_FIELDS = (
    "name",
    "owner_name",
    "license_type",
    "quantity",
    "expire_date",
)

ASSET_LOG_FIELDS = (
    "name",
    "category_id",
    "department_name",
    "user_name",
    "status",
    "model_name",
    "purchase_date",
)

VEHICLE_LOG_FIELDS = (
    "company_name",
    "vehicle_number",
    "vehicle_name",
    "driver_name",
    "ownership_type",
    "insurance_company",
    "insurance_type",
    "insurance_start_date",
    "insurance_end_date",
)

VEHICLE_INSURANCE_HISTORY_LOG_FIELDS = (
    "vehicle_id",
    "start_date",
    "end_date",
    "insurance_type",
    "driver_name",
    "amount",
    "payment_method",
    "note",
)


def serialize_software_activity_data(item: SoftwareItem) -> Dict[str, object]:
    return serialize_model_fields(item, SOFTWARE_LOG_FIELDS)


def serialize_asset_activity_data(item: Asset) -> Dict[str, object]:
    return serialize_model_fields(item, ASSET_LOG_FIELDS)


def serialize_vehicle_activity_data(item: CompanyVehicle) -> Dict[str, object]:
    return serialize_model_fields(item, VEHICLE_LOG_FIELDS)


def serialize_vehicle_insurance_history_activity_data(
    item: VehicleInsuranceHistory,
) -> Dict[str, object]:
    return serialize_model_fields(item, VEHICLE_INSURANCE_HISTORY_LOG_FIELDS)


def serialize_model_fields(item: object, field_names: tuple[str, ...]) -> Dict[str, object]:
    data: Dict[str, object] = {}
    for field_name in field_names:
        value = getattr(item, field_name)
        if isinstance(value, (date, datetime)):
            data[field_name] = value.isoformat()
        elif isinstance(value, Decimal):
            data[field_name] = int(value) if value == value.to_integral_value() else float(value)
        elif hasattr(value, "value"):
            data[field_name] = value.value
        else:
            data[field_name] = value
    return data


def record_software_activity(
    db: Session,
    *,
    action_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    return record_activity_log(
        db,
        menu_name="SW 현황",
        action_type=action_type,
        target_type="software",
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def record_asset_activity(
    db: Session,
    *,
    action_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    return record_activity_log(
        db,
        menu_name="자산 관리",
        action_type=action_type,
        target_type="asset",
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def record_vehicle_activity(
    db: Session,
    *,
    action_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    return record_activity_log(
        db,
        menu_name="법인차량 관리",
        action_type=action_type,
        target_type="vehicle",
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def record_vehicle_insurance_history_activity(
    db: Session,
    *,
    action_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    return record_activity_log(
        db,
        menu_name="차량 보험 이력",
        action_type=action_type,
        target_type="vehicle_insurance_history",
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )


def record_activity_log(
    db: Session,
    *,
    menu_name: str,
    action_type: str,
    target_type: str,
    target_id: Optional[int],
    target_name: Optional[str],
    actor_ip: Optional[str],
    user_agent: Optional[str],
    summary: Optional[str] = None,
    before_data: Optional[Dict[str, object]] = None,
    after_data: Optional[Dict[str, object]] = None,
) -> SystemActivityLog:
    log = SystemActivityLog(
        menu_name=menu_name,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        actor_ip=actor_ip,
        actor_name=None,
        user_agent=user_agent,
        summary=summary,
        before_data=before_data,
        after_data=after_data,
    )
    db.add(log)
    return log


def get_activity_logs(
    db: Session,
    limit: int = 100,
    *,
    target_type: Optional[str] = None,
) -> List[SystemActivityLog]:
    safe_limit = min(max(limit, 1), 200)
    statement = select(SystemActivityLog)
    if target_type:
        statement = statement.where(SystemActivityLog.target_type == target_type)
    statement = statement.order_by(
        SystemActivityLog.created_at.desc(),
        SystemActivityLog.id.desc(),
    ).limit(safe_limit)
    return list(db.scalars(statement).all())
