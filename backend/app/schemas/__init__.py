from app.schemas.activity_log import ActivityLogRead
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.company_vehicle import (
    CompanyVehicleCreate,
    CompanyVehicleRead,
    CompanyVehicleSummary,
    CompanyVehicleUpdate,
)
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.schemas.history import AssetHistoryCreate, AssetHistoryRead

__all__ = [
    "ActivityLogRead",
    "AssetCreate",
    "AssetHistoryCreate",
    "AssetHistoryRead",
    "AssetRead",
    "AssetUpdate",
    "CategoryCreate",
    "CategoryRead",
    "CategoryUpdate",
    "CompanyVehicleCreate",
    "CompanyVehicleRead",
    "CompanyVehicleSummary",
    "CompanyVehicleUpdate",
    "DepartmentCreate",
    "DepartmentRead",
    "DepartmentUpdate",
]
