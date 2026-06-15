from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.history import AssetActionType


class AssetHistoryBase(BaseModel):
    asset_id: int
    action_type: AssetActionType
    field_name: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    memo: str | None = None


class AssetHistoryCreate(AssetHistoryBase):
    pass


class AssetHistoryRead(AssetHistoryBase):
    id: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
