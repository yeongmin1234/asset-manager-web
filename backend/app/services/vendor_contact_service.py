from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.vendor_contact import VendorContact
from app.models.attachment import AttachmentEntityType
from app.schemas.vendor_contact import VendorContactCreate, VendorContactRead, VendorContactUpdate
from app.services.attachment_service import ensure_no_attachments


class VendorContactNotFoundError(Exception):
    pass


def list_vendor_contacts(
    db: Session,
    *,
    category: Optional[str] = None,
    keyword: Optional[str] = None,
) -> List[VendorContact]:
    statement = select(VendorContact).where(VendorContact.is_deleted.is_(False))

    normalized_category = (category or "").strip()
    if normalized_category:
        statement = statement.where(VendorContact.category == normalized_category)

    normalized_keyword = (keyword or "").strip()
    if normalized_keyword:
        keyword_pattern = "%{}%".format(normalized_keyword)
        statement = statement.where(
            or_(
                VendorContact.company_name.ilike(keyword_pattern),
                VendorContact.task_name.ilike(keyword_pattern),
                VendorContact.manager_name.ilike(keyword_pattern),
                VendorContact.phone.ilike(keyword_pattern),
                VendorContact.email.ilike(keyword_pattern),
                VendorContact.memo.ilike(keyword_pattern),
            )
        )

    statement = statement.order_by(
        VendorContact.is_favorite.desc(),
        VendorContact.updated_at.desc(),
        VendorContact.id.desc(),
    )
    return list(db.scalars(statement).all())


def get_vendor_contact(db: Session, contact_id: int) -> VendorContact:
    contact = db.get(VendorContact, contact_id)
    if contact is None or contact.is_deleted:
        raise VendorContactNotFoundError()
    return contact


def create_vendor_contact(db: Session, payload: VendorContactCreate) -> VendorContact:
    contact = VendorContact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def update_vendor_contact(
    db: Session,
    contact_id: int,
    payload: VendorContactUpdate,
) -> VendorContact:
    contact = get_vendor_contact(db, contact_id)
    for field_name, value in payload.model_dump().items():
        setattr(contact, field_name, value)
    contact.updated_at = datetime.now(timezone.utc)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def delete_vendor_contact(db: Session, contact_id: int) -> VendorContactRead:
    contact = get_vendor_contact(db, contact_id)
    ensure_no_attachments(db, AttachmentEntityType.VENDOR_CONTACT, contact_id)
    deleted_contact = VendorContactRead.model_validate(contact)
    contact.is_deleted = True
    contact.updated_at = datetime.now(timezone.utc)
    db.add(contact)
    db.commit()
    return deleted_contact
