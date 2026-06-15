from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.history import AssetActionType, AssetHistory


def record_asset_history(
    db: Session,
    *,
    asset_id: int,
    action_type: AssetActionType,
    field_name: str | None = None,
    old_value: object | None = None,
    new_value: object | None = None,
    memo: str | None = None,
) -> AssetHistory:
    history = AssetHistory(
        asset_id=asset_id,
        action_type=action_type,
        field_name=field_name,
        old_value=None if old_value is None else str(old_value),
        new_value=None if new_value is None else str(new_value),
        memo=memo,
    )
    db.add(history)
    return history


def record_asset_created(db: Session, asset_id: int) -> AssetHistory:
    return record_asset_history(
        db,
        asset_id=asset_id,
        action_type=AssetActionType.CREATED,
        memo="자산 등록",
    )


def record_asset_disposed(
    db: Session,
    asset_id: int,
    *,
    old_value: object | None = None,
    new_value: object | None = None,
) -> AssetHistory:
    return record_asset_history(
        db,
        asset_id=asset_id,
        action_type=AssetActionType.DISPOSED,
        field_name="status",
        old_value=old_value,
        new_value=new_value,
        memo="자산 폐기",
    )


def record_asset_deleted(
    db: Session,
    asset_id: int,
    *,
    new_value: object | None = None,
) -> AssetHistory:
    return record_asset_history(
        db,
        asset_id=asset_id,
        action_type=AssetActionType.DELETED,
        field_name="deleted_at",
        new_value=new_value,
        memo="자산 삭제",
    )


def get_asset_history(db: Session, asset_id: int) -> list[AssetHistory]:
    statement = (
        select(AssetHistory)
        .where(AssetHistory.asset_id == asset_id)
        .order_by(AssetHistory.changed_at.desc(), AssetHistory.id.desc())
    )
    return list(db.scalars(statement).all())
