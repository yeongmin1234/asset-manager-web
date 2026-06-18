from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.paju_fire_insurance import PajuFireInsuranceContract
from app.schemas.paju_fire_insurance import (
    PajuFireInsuranceContractCreate,
    PajuFireInsuranceContractRead,
    PajuFireInsuranceContractUpdate,
    PajuFireInsuranceSummary,
)
from app.services.activity_log_service import (
    record_paju_fire_insurance_activity,
    serialize_paju_fire_insurance_activity_data,
)


class PajuFireInsuranceContractNotFoundError(Exception):
    pass


def get_paju_fire_insurance_contracts(
    db: Session,
    *,
    location_group: Optional[str] = None,
    contractor: Optional[str] = None,
    insurer_name: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[PajuFireInsuranceContract]:
    statement = select(PajuFireInsuranceContract)
    if location_group:
        statement = statement.where(PajuFireInsuranceContract.location_group == location_group)
    if contractor:
        statement = statement.where(PajuFireInsuranceContract.contractor == contractor)
    if insurer_name:
        statement = statement.where(PajuFireInsuranceContract.insurer_name.ilike(f"%{insurer_name}%"))
    if keyword:
        keyword_pattern = f"%{keyword}%"
        statement = statement.where(
            or_(
                PajuFireInsuranceContract.warehouse_name.ilike(keyword_pattern),
                PajuFireInsuranceContract.insurer_name.ilike(keyword_pattern),
                PajuFireInsuranceContract.contractor.ilike(keyword_pattern),
                PajuFireInsuranceContract.note.ilike(keyword_pattern),
            )
        )
    statement = statement.order_by(
        PajuFireInsuranceContract.created_at.desc(),
        PajuFireInsuranceContract.id.desc(),
    )
    return list(db.scalars(statement).all())


def create_paju_fire_insurance_contract(
    db: Session,
    payload: PajuFireInsuranceContractCreate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> PajuFireInsuranceContract:
    contract = PajuFireInsuranceContract(**payload.model_dump())
    db.add(contract)
    db.flush()
    record_paju_fire_insurance_activity(
        db,
        action_type="create",
        target_id=contract.id,
        target_name=format_paju_fire_insurance_target_name(contract),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[파주화재보험] 계약 등록: {format_paju_fire_insurance_target_name(contract)}",
        after_data=serialize_paju_fire_insurance_activity_data(contract),
    )
    db.commit()
    db.refresh(contract)
    return contract


def get_paju_fire_insurance_contract(
    db: Session,
    contract_id: int,
) -> PajuFireInsuranceContract:
    contract = db.scalar(
        select(PajuFireInsuranceContract).where(PajuFireInsuranceContract.id == contract_id)
    )
    if contract is None:
        raise PajuFireInsuranceContractNotFoundError(
            f"Paju fire insurance contract not found: {contract_id}"
        )
    return contract


def update_paju_fire_insurance_contract(
    db: Session,
    contract_id: int,
    payload: PajuFireInsuranceContractUpdate,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> PajuFireInsuranceContract:
    contract = get_paju_fire_insurance_contract(db, contract_id)
    before_data = serialize_paju_fire_insurance_activity_data(contract)
    for field_name, value in payload.model_dump().items():
        setattr(contract, field_name, value)
    contract.updated_at = datetime.now(timezone.utc)
    db.flush()
    record_paju_fire_insurance_activity(
        db,
        action_type="update",
        target_id=contract.id,
        target_name=format_paju_fire_insurance_target_name(contract),
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[파주화재보험] 계약 수정: {format_paju_fire_insurance_target_name(contract)}",
        before_data=before_data,
        after_data=serialize_paju_fire_insurance_activity_data(contract),
    )
    db.commit()
    db.refresh(contract)
    return contract


def delete_paju_fire_insurance_contract(
    db: Session,
    contract_id: int,
    *,
    actor_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> PajuFireInsuranceContractRead:
    contract = get_paju_fire_insurance_contract(db, contract_id)
    before_data = serialize_paju_fire_insurance_activity_data(contract)
    target_name = format_paju_fire_insurance_target_name(contract)
    deleted_contract = PajuFireInsuranceContractRead.model_validate(contract)
    record_paju_fire_insurance_activity(
        db,
        action_type="delete",
        target_id=contract.id,
        target_name=target_name,
        actor_ip=actor_ip,
        user_agent=user_agent,
        summary=f"[파주화재보험] 계약 삭제: {target_name}",
        before_data=before_data,
    )
    db.delete(contract)
    db.commit()
    return deleted_contract


def get_paju_fire_insurance_summary(db: Session) -> PajuFireInsuranceSummary:
    today = date.today()
    deadline = today + timedelta(days=90)
    ending_soon_condition = PajuFireInsuranceContract.contract_end_date.between(today, deadline)

    row = db.execute(
        select(
            func.count(PajuFireInsuranceContract.id).label("total"),
            func.coalesce(
                func.sum(
                    case(
                        (PajuFireInsuranceContract.location_group == "송촌동", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("songchon"),
            func.coalesce(
                func.sum(
                    case(
                        (PajuFireInsuranceContract.location_group == "신촌동", 1),
                        else_=0,
                    )
                ),
                0,
            ).label("sinchon"),
            func.coalesce(func.sum(PajuFireInsuranceContract.monthly_premium), 0).label(
                "monthly_premium_total"
            ),
            func.coalesce(func.sum(PajuFireInsuranceContract.annual_premium), 0).label(
                "annual_premium_total"
            ),
            func.coalesce(func.sum(case((ending_soon_condition, 1), else_=0)), 0).label(
                "ending_soon"
            ),
        )
    ).one()

    return PajuFireInsuranceSummary(
        total=int(row.total or 0),
        songchon=int(row.songchon or 0),
        sinchon=int(row.sinchon or 0),
        monthly_premium_total=int(row.monthly_premium_total or 0),
        annual_premium_total=int(row.annual_premium_total or 0),
        ending_soon=int(row.ending_soon or 0),
    )


def format_paju_fire_insurance_target_name(contract: PajuFireInsuranceContract) -> str:
    parts = [
        contract.location_group,
        contract.insurer_name,
        contract.contractor,
    ]
    return " / ".join(part for part in parts if part) or f"파주화재보험 #{contract.id}"
