from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class DepartmentBase(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentRead(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentLookup(DepartmentBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
