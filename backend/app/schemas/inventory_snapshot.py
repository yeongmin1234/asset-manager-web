from datetime import datetime, time
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class InventoryScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    run_time: time
    timezone: str = Field(default="Asia/Seoul", max_length=64)
    is_active: bool = False
    target_mode: Literal["selected_items", "all_supported_items"] = "selected_items"
    target_item_codes: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value):
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value):
        normalized = value.strip()
        try:
            ZoneInfo(normalized)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("유효한 IANA 시간대를 입력해주세요.") from exc
        return normalized

    @field_validator("target_item_codes")
    @classmethod
    def normalize_item_codes(cls, values):
        result = list(dict.fromkeys(value.strip().upper() for value in values if value.strip()))
        if any(len(value) > 20 for value in result):
            raise ValueError("품목코드는 20자 이하로 입력해주세요.")
        return result


class InventoryScheduleCreate(InventoryScheduleBase):
    pass


class InventoryScheduleUpdate(InventoryScheduleBase):
    pass


class InventoryScheduleActiveRequest(BaseModel):
    is_active: bool


class InventoryScheduleRead(InventoryScheduleBase):
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InventoryJobRunRead(BaseModel):
    id: int
    schedule_id: Optional[int] = None
    snapshot_group_id: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str
    requested_item_count: int
    success_count: int
    failed_count: int
    snapshot_count: int
    error_code: Optional[str] = None
    safe_error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StoredWarehouseInventory(BaseModel):
    warehouse_code: str
    warehouse_name: Optional[str] = None
    quantity: Decimal


class StoredInventoryItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    unit: Optional[str] = None
    total_quantity: Decimal
    warehouses: List[StoredWarehouseInventory] = Field(default_factory=list)


class InventorySnapshotGroupResponse(BaseModel):
    snapshot_group_id: Optional[str] = None
    schedule_id: Optional[int] = None
    snapshot_at: Optional[datetime] = None
    total: int
    items: List[StoredInventoryItem]


class InventorySnapshotHistoryItem(BaseModel):
    snapshot_group_id: str
    schedule_id: Optional[int] = None
    snapshot_at: datetime
    item_code: str
    item_name: Optional[str] = None
    unit: Optional[str] = None
    total_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class InventorySnapshotCompareItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    previous_quantity: Decimal
    current_quantity: Decimal
    difference: Decimal


class InventorySnapshotCompareResponse(BaseModel):
    previous_snapshot_at: Optional[datetime] = None
    current_snapshot_at: Optional[datetime] = None
    total: int
    items: List[InventorySnapshotCompareItem]


class InventorySnapshotAdminRead(BaseModel):
    id: int
    snapshot_group_id: str
    schedule_id: Optional[int] = None
    snapshot_at: datetime
    row_type: str
    item_code: str
    item_name: Optional[str] = None
    unit: Optional[str] = None
    warehouse_code: str
    warehouse_name: Optional[str] = None
    quantity: Decimal
    total_quantity: Decimal

    model_config = ConfigDict(from_attributes=True)


class InventoryChangeItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    unit: Optional[str] = None
    before_quantity: Decimal
    after_quantity: Decimal
    change_quantity: Decimal
    change_rate: Optional[Decimal] = None
    change_rate_label: Optional[str] = None
    status: str
    total_quantity: Decimal
    warehouses: List[StoredWarehouseInventory] = Field(default_factory=list)


class InventoryChangeResponse(BaseModel):
    success: bool
    available: bool
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    start_snapshot_group_id: Optional[str] = None
    end_snapshot_group_id: Optional[str] = None
    start_schedule_id: Optional[int] = None
    end_schedule_id: Optional[int] = None
    selection_note: str
    total_items: int
    total: int
    increased_count: int
    decreased_count: int
    unchanged_count: int
    largest_increase: Optional[InventoryChangeItem] = None
    largest_decrease: Optional[InventoryChangeItem] = None
    items: List[InventoryChangeItem]
    message: str
    answer: str
    analysis: dict
