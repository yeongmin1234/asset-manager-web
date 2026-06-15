from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.history import AssetHistoryCreate, AssetHistoryRead

__all__ = [
    "AssetCreate",
    "AssetHistoryCreate",
    "AssetHistoryRead",
    "AssetRead",
    "AssetUpdate",
    "CategoryCreate",
    "CategoryRead",
    "CategoryUpdate",
    "DepartmentCreate",
    "DepartmentRead",
    "DepartmentUpdate",
]
