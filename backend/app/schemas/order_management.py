from typing import Literal

from pydantic import BaseModel


class OrderManagementReady(BaseModel):
    status: Literal["ready"] = "ready"
    message: str = "발주관리 기능 준비 중"
