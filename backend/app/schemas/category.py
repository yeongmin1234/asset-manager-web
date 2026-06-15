from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CategoryBase(BaseModel):
    name: str
    sort_order: int = 0
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryLookup(CategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
