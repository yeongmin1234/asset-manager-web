from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class OrderManagementReady(BaseModel):
    status: Literal["ready"] = "ready"
    message: str = "발주관리 기능 준비 중"


class OrderDashboardResponse(OrderManagementReady):
    today_count: int = 0
    success_count: int = 0
    mapping_required_count: int = 0
    error_count: int = 0


class OrderListResponse(OrderManagementReady):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: int = 0
