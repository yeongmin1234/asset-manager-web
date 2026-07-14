from app.models.activity_log import SystemActivityLog
from app.models.audit_log import AuditLog
from app.models.sidebar_menu_label import SidebarMenuLabel
from app.models.admin_setting import AdminSetting
from app.models.asset import Asset, AssetStatus
from app.models.attachment import Attachment, AttachmentEntityType
from app.models.beverage_order_record import BeverageOrderRecord
from app.models.category import Category
from app.models.company_vehicle import CompanyVehicle, VehicleOwnershipType
from app.models.dashboard_notice import DashboardNotice, DashboardNoticeType
from app.models.department import Department
from app.models.expiration_schedule import (
    ExpirationSchedule,
    ExpirationScheduleCategory,
    ExpirationScheduleStatus,
)
from app.models.history import AssetActionType, AssetHistory
from app.models.install_file import InstallFile
from app.models.hr_account import HrAccount
from app.models.login_access_log import LoginAccessLog
from app.models.menu_access_log import MenuAccessLog
from app.models.menu_visibility_setting import MenuVisibilitySetting
from app.models.network_credential import (
    NetworkCredential,
    NetworkCredentialCategory,
    NetworkCredentialImportance,
)
from app.models.paju_fire_insurance import PajuFireInsuranceContract
from app.models.software_item import SoftwareItem, SoftwareLicenseType
from app.models.vendor_contact import VendorContact
from app.models.vehicle_insurance_history import VehicleInsuranceHistory
from app.models.work_manual import WorkManual
from app.models.user import User

__all__ = [
    "Asset",
    "AuditLog",
    "SidebarMenuLabel",
    "AssetActionType",
    "AssetHistory",
    "AssetStatus",
    "Attachment",
    "AttachmentEntityType",
    "AdminSetting",
    "BeverageOrderRecord",
    "Category",
    "CompanyVehicle",
    "DashboardNotice",
    "DashboardNoticeType",
    "Department",
    "ExpirationSchedule",
    "ExpirationScheduleCategory",
    "ExpirationScheduleStatus",
    "InstallFile",
    "HrAccount",
    "LoginAccessLog",
    "MenuAccessLog",
    "MenuVisibilitySetting",
    "NetworkCredential",
    "NetworkCredentialCategory",
    "NetworkCredentialImportance",
    "PajuFireInsuranceContract",
    "SystemActivityLog",
    "SoftwareItem",
    "SoftwareLicenseType",
    "VendorContact",
    "VehicleInsuranceHistory",
    "VehicleOwnershipType",
    "WorkManual",
    "User",
]
