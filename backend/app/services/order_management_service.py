"""Response helpers for the order management screens before processing is implemented."""

from typing import List

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.online_order_channel import OnlineOrderChannel
from app.schemas.order_management import OrderDashboardResponse, OrderListResponse, OrderManagementReady


# Add a code only when its actual parser is registered. Channel rows cannot
# claim processing support, and the processing endpoint is still a 501 placeholder.
PROCESSING_SUPPORTED_CODES = frozenset()


def list_order_channels(db: Session, active_only: bool = False) -> List[OnlineOrderChannel]:
    query = select(OnlineOrderChannel).order_by(OnlineOrderChannel.id)
    if active_only:
        query = query.where(OnlineOrderChannel.is_active.is_(True))
    return list(db.scalars(query).all())


def create_order_channel(db: Session, payload, user_id: int) -> OnlineOrderChannel:
    if payload.is_default and not payload.is_active:
        raise HTTPException(status_code=422, detail="미사용 채널은 기본 채널로 지정할 수 없습니다.")
    if db.scalar(select(OnlineOrderChannel.id).where(OnlineOrderChannel.code == payload.code)) is not None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 채널 코드입니다.")
    if payload.is_default:
        db.execute(update(OnlineOrderChannel).where(OnlineOrderChannel.is_default.is_(True)).values(is_default=False, updated_by=user_id))
    channel = OnlineOrderChannel(**payload.model_dump(), created_by=user_id, updated_by=user_id)
    db.add(channel)
    return _commit_channel(db, channel)


def update_order_channel(db: Session, channel_id: int, payload, user_id: int) -> OnlineOrderChannel:
    channel = db.get(OnlineOrderChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="채널을 찾을 수 없습니다.")
    if payload.is_default and not payload.is_active:
        raise HTTPException(status_code=422, detail="미사용 채널은 기본 채널로 지정할 수 없습니다.")
    if channel.is_default and not payload.is_default and payload.is_active:
        raise HTTPException(status_code=422, detail="다른 채널을 기본으로 지정한 뒤 해제할 수 있습니다.")
    replacement_id = None
    if channel.is_default and not payload.is_active:
        replacement_id = db.scalar(
            select(OnlineOrderChannel.id)
            .where(OnlineOrderChannel.id != channel_id, OnlineOrderChannel.is_active.is_(True))
            .order_by(OnlineOrderChannel.id)
            .limit(1)
        )
    if payload.is_default:
        db.execute(
            update(OnlineOrderChannel)
            .where(OnlineOrderChannel.is_default.is_(True), OnlineOrderChannel.id != channel_id)
            .values(is_default=False, updated_by=user_id)
        )
    for key, value in payload.model_dump().items():
        setattr(channel, key, value)
    channel.updated_by = user_id
    if replacement_id is not None:
        db.flush()
        db.execute(
            update(OnlineOrderChannel).where(OnlineOrderChannel.id == replacement_id)
            .values(is_default=True, updated_by=user_id)
        )
    return _commit_channel(db, channel)


def _commit_channel(db: Session, channel: OnlineOrderChannel) -> OnlineOrderChannel:
    try:
        db.commit()
        db.refresh(channel)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="채널 코드 또는 기본 채널이 중복됩니다.") from exc
    return channel


def ready_response() -> OrderManagementReady:
    return OrderManagementReady()


def empty_dashboard() -> OrderDashboardResponse:
    return OrderDashboardResponse()


def empty_list() -> OrderListResponse:
    return OrderListResponse()
