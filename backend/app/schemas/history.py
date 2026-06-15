from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.history import AssetActionType


class AssetHistoryBase(BaseModel):
    asset_id: int
    action_type: AssetActionType
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    memo: Optional[str] = None


class AssetHistoryCreate(AssetHistoryBase):
    pass


class AssetHistoryRead(AssetHistoryBase):
    id: int
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)
