from decimal import Decimal
from typing import Any, Dict, List, Optional

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
    rank: Optional[int] = None
    difference: Optional[Decimal] = None


class AggregatedInventoryResponse(BaseModel):
    success: bool
    authenticated: bool
    total: int
    items: List[AggregatedInventoryItem]
    message: str
    response_time_ms: int
    answer: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None


class ProductMasterItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    size: Optional[str] = None
    unit: Optional[str] = None
    match_score: Optional[float] = None
    match_reason: Optional[str] = None
    match_type: Optional[str] = None


class ProductMasterListResponse(BaseModel):
    success: bool = True
    total: int
    page: int
    page_size: int
    items: List[ProductMasterItem]
    data_source: str = "product_master_cache"
    match_type: str = "all"


class WarehouseMasterItem(BaseModel):
    warehouse_code: str
    warehouse_name: str
    location_type: str = "warehouse"


class WarehouseMasterListResponse(BaseModel):
    success: bool = True
    total: int
    limit: int
    offset: int
    items: List[WarehouseMasterItem]
    cache_status: str
    data_source: str


class WarehouseProductInventoryItem(BaseModel):
    item_code: str
    item_name: Optional[str] = None
    size: Optional[str] = None
    unit: Optional[str] = None
    quantity: Decimal
    warehouse_code: str
    warehouse_name: Optional[str] = None


class WarehouseInventorySummary(BaseModel):
    item_count: int
    positive_item_count: int
    zero_item_count: int
    negative_item_count: int


class WarehouseInventoryResponse(BaseModel):
    success: bool = True
    warehouse_code: str
    warehouse_name: str
    summary: WarehouseInventorySummary
    total: int
    limit: int
    offset: int
    items: List[WarehouseProductInventoryItem]
    include_zero: bool
    sort: str
    cache_hit: bool
