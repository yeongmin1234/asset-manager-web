from app.schemas.activity_log import ActivityLogRead
from app.schemas.admin import (
    AdminPasswordResetRequest,
    AdminPasswordResetResponse,
)
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
from app.schemas.network_credential import (
    NetworkCredentialCreate,
    NetworkCredentialRead,
    NetworkCredentialUpdate,
)
from app.schemas.server_operation import (
    ScmMariaDbRestartDryRunRequest,
    ScmMariaDbRestartDryRunResponse,
    ScmStatusResponse,
)
from app.schemas.vehicle_insurance_history import (
    VehicleInsuranceHistoryCreate,
    VehicleInsuranceHistoryRead,
    VehicleInsuranceHistoryUpdate,
)

__all__ = [
    "ActivityLogRead",
    "AdminPasswordResetRequest",
    "AdminPasswordResetResponse",
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
    "NetworkCredentialCreate",
    "NetworkCredentialRead",
    "NetworkCredentialUpdate",
    "ScmMariaDbRestartDryRunRequest",
    "ScmMariaDbRestartDryRunResponse",
    "ScmStatusResponse",
    "VehicleInsuranceHistoryCreate",
    "VehicleInsuranceHistoryRead",
    "VehicleInsuranceHistoryUpdate",
]
