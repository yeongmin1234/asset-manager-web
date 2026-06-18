from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.paju_fire_insurance import (
    PajuFireInsuranceContractCreate,
    PajuFireInsuranceContractRead,
    PajuFireInsuranceContractUpdate,
    PajuFireInsuranceSummary,
)
from app.services.paju_fire_insurance_service import (
    PajuFireInsuranceContractNotFoundError,
    create_paju_fire_insurance_contract,
    delete_paju_fire_insurance_contract,
    get_paju_fire_insurance_contracts,
    get_paju_fire_insurance_summary,
    update_paju_fire_insurance_contract,
)


router = APIRouter(prefix="/paju-fire-insurance", tags=["paju-fire-insurance"])


@router.get("", response_model=List[PajuFireInsuranceContractRead])
def list_paju_fire_insurance_contracts(
    location_group: Optional[str] = Query(default=None),
    contractor: Optional[str] = Query(default=None),
    insurer_name: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> List[PajuFireInsuranceContractRead]:
    try:
        return get_paju_fire_insurance_contracts(
            db,
            location_group=location_group,
            contractor=contractor,
            insurer_name=insurer_name,
            keyword=keyword,
        )
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading Paju fire insurance contracts.",
        ) from exc


@router.get("/summary", response_model=PajuFireInsuranceSummary)
def read_paju_fire_insurance_summary(
    db: Session = Depends(get_db),
) -> PajuFireInsuranceSummary:
    try:
        return get_paju_fire_insurance_summary(db)
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while loading Paju fire insurance summary.",
        ) from exc


@router.post("", response_model=PajuFireInsuranceContractRead, status_code=status.HTTP_201_CREATED)
def create_new_paju_fire_insurance_contract(
    request: Request,
    payload: PajuFireInsuranceContractCreate,
    db: Session = Depends(get_db),
) -> PajuFireInsuranceContractRead:
    try:
        return create_paju_fire_insurance_contract(
            db,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while creating Paju fire insurance contract.",
        ) from exc


@router.put("/{contract_id}", response_model=PajuFireInsuranceContractRead)
def update_existing_paju_fire_insurance_contract(
    request: Request,
    contract_id: int,
    payload: PajuFireInsuranceContractUpdate,
    db: Session = Depends(get_db),
) -> PajuFireInsuranceContractRead:
    try:
        return update_paju_fire_insurance_contract(
            db,
            contract_id,
            payload,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except PajuFireInsuranceContractNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paju fire insurance contract not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while updating Paju fire insurance contract.",
        ) from exc


@router.delete("/{contract_id}", response_model=PajuFireInsuranceContractRead)
def delete_existing_paju_fire_insurance_contract(
    request: Request,
    contract_id: int,
    db: Session = Depends(get_db),
) -> PajuFireInsuranceContractRead:
    try:
        return delete_paju_fire_insurance_contract(
            db,
            contract_id,
            actor_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except PajuFireInsuranceContractNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paju fire insurance contract not found.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed while deleting Paju fire insurance contract.",
        ) from exc
