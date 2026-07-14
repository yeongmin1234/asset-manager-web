from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.hr_account import HrAccount
from app.schemas.hr_account import HrAccountCreate, HrAccountUpdate


class HrAccountNotFoundError(Exception):
    pass


def list_hr_accounts(db: Session, keyword: Optional[str] = None) -> List[HrAccount]:
    statement = select(HrAccount).where(HrAccount.deleted_at.is_(None))
    normalized = (keyword or "").strip()
    if normalized:
        pattern = "%{}%".format(normalized)
        statement = statement.where(or_(
            HrAccount.department.ilike(pattern), HrAccount.name.ilike(pattern),
            HrAccount.dowoffice.ilike(pattern), HrAccount.erp.ilike(pattern),
            HrAccount.scm.ilike(pattern), HrAccount.nas.ilike(pattern),
        ))
    return list(db.scalars(statement.order_by(HrAccount.created_at.desc(), HrAccount.id.desc())).all())


def get_hr_account(db: Session, account_id: int) -> HrAccount:
    account = db.get(HrAccount, account_id)
    if account is None or account.deleted_at is not None:
        raise HrAccountNotFoundError()
    return account


def create_hr_account(db: Session, payload: HrAccountCreate) -> HrAccount:
    account = HrAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def update_hr_account(db: Session, account_id: int, payload: HrAccountUpdate) -> HrAccount:
    account = get_hr_account(db, account_id)
    for key, value in payload.model_dump().items():
        setattr(account, key, value)
    account.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    return account


def delete_hr_account(db: Session, account_id: int) -> HrAccount:
    account = get_hr_account(db, account_id)
    account.deleted_at = datetime.now(timezone.utc)
    account.updated_at = account.deleted_at
    db.commit()
    db.refresh(account)
    return account
