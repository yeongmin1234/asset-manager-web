from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel


class InventoryItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    quantity: Decimal
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    unit: Optional[str] = None
    updated_at: Optional[str] = None


class InventorySearchResponse(BaseModel):
    success: bool
    authenticated: bool
    total: int
    items: List[InventoryItem]
    message: str
    response_time_ms: int


class WarehouseInventoryItem(BaseModel):
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None
    quantity: Decimal


class AggregatedInventoryItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    size: Optional[str] = None
    unit: Optional[str] = None
    total_quantity: Decimal
    warehouses: List[WarehouseInventoryItem]


class AggregatedInventoryResponse(BaseModel):
    success: bool
    authenticated: bool
    total: int
    items: List[AggregatedInventoryItem]
    message: str
    response_time_ms: int
