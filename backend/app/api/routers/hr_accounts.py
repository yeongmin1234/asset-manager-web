from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.hr_account import HrAccountCreate, HrAccountRead, HrAccountUpdate
from app.services.hr_account_service import (
    HrAccountNotFoundError, create_hr_account, delete_hr_account,
    list_hr_accounts, update_hr_account,
)

router = APIRouter(prefix="/hr/accounts", tags=["hr-accounts"])


@router.get("", response_model=List[HrAccountRead])
def read_hr_accounts(keyword: Optional[str] = Query(default=None), db: Session = Depends(get_db)):
    try:
        return list_hr_accounts(db, keyword)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="계정 현황을 불러오는 중 DB 연결에 실패했습니다.") from exc


@router.post("", response_model=HrAccountRead, status_code=status.HTTP_201_CREATED)
def create_new_hr_account(payload: HrAccountCreate, db: Session = Depends(get_db)):
    try:
        return create_hr_account(db, payload)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 등록하는 중 DB 연결에 실패했습니다.") from exc


@router.put("/{account_id}", response_model=HrAccountRead)
def update_existing_hr_account(account_id: int, payload: HrAccountUpdate, db: Session = Depends(get_db)):
    try:
        return update_hr_account(db, account_id, payload)
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 수정하는 중 DB 연결에 실패했습니다.") from exc


@router.delete("/{account_id}", response_model=HrAccountRead)
def delete_existing_hr_account(account_id: int, db: Session = Depends(get_db)):
    try:
        return delete_hr_account(db, account_id)
    except HrAccountNotFoundError as exc:
        raise HTTPException(status_code=404, detail="계정 현황을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="계정 현황을 삭제하는 중 DB 연결에 실패했습니다.") from exc
