import logging
from contextlib import asynccontextmanager
from typing import List
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.auth import get_current_user, require_admin, require_menu_permission
from app.core.config import REQUIRED_CORS_ORIGINS, settings
from app.api.routers import (
    activity_logs,
    admin,
    ai_assistant,
    attachments,
    auth,
    beverage_orders,
    company_vehicles,
    dashboard_notices,
    ecount_integration,
    expiration_schedules,
    install_files,
    inventory,
    inventory_alerts_admin,
    hr_accounts,
    menu_access_logs,
    menu_visibility,
    network_credentials,
    network_status,
    order_management,
    paju_fire_insurance,
    recall_preview,
    recall_targets,
    server_operations,
    sidebar_menu_labels,
    software,
    stats,
    users,
    vendor_contacts,
    vehicle_insurance_histories,
    visitors,
    work_manuals,
)
from app.routers import assets, categories, departments, health
from app.services.inventory_scheduler_service import get_inventory_scheduler
from app.services.download_service import DownloadMiddleware, router as downloads_router


def get_cors_origins() -> List[str]:
    # Required origins remain available when CORS_ORIGINS is missing or empty
    # in the NAS environment. Explicit env origins may safely add entries.
    return list(
        dict.fromkeys([*settings.cors_origin_list, *REQUIRED_CORS_ORIGINS])
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    scheduler = get_inventory_scheduler()
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(DownloadMiddleware)
cors_origins = get_cors_origins()
logging.getLogger("uvicorn.error").info(
    "CORS allow_origins=%s",
    cors_origins,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Range", "Accept-Ranges"],
)

Path(settings.upload_dir).resolve().mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(Path(settings.upload_dir).resolve())),
    name="uploads",
)

app.include_router(health.router)
app.include_router(downloads_router)
app.include_router(auth.router)
app.include_router(menu_access_logs.router)
app.include_router(attachments.router)
app.include_router(ai_assistant.router, dependencies=[Depends(get_current_user)])
app.include_router(inventory.router, dependencies=[Depends(get_current_user)])

authenticated_user = [Depends(get_current_user)]
admin_only = [Depends(require_admin)]

app.include_router(sidebar_menu_labels.router, dependencies=authenticated_user)
app.include_router(menu_visibility.router, dependencies=authenticated_user)

assets_access = [Depends(require_menu_permission("assets"))]
dashboard_access = [Depends(require_menu_permission("dashboard"))]
stats_access = [Depends(require_menu_permission("dashboard", "statistics"))]

# User-facing routes are readable only when the account has the matching menu permission.
# Non-safe methods remain admin-only inside require_menu_permission.
app.include_router(categories.router, dependencies=assets_access)
app.include_router(departments.router, dependencies=assets_access)
app.include_router(assets.router, dependencies=assets_access)
app.include_router(stats.router, dependencies=stats_access)
app.include_router(beverage_orders.router, dependencies=[Depends(require_menu_permission("drink_orders"))])
app.include_router(dashboard_notices.router, dependencies=dashboard_access)
app.include_router(expiration_schedules.router, dependencies=[Depends(require_menu_permission("expiration_schedules"))])
app.include_router(work_manuals.router, dependencies=[Depends(require_menu_permission("work_manual"))])
app.include_router(vendor_contacts.router, dependencies=[Depends(require_menu_permission("vendor_contacts"))])
app.include_router(hr_accounts.router, dependencies=[Depends(require_menu_permission("hr_list"))])
app.include_router(recall_preview.router)
app.include_router(recall_targets.router)
app.include_router(order_management.router)
app.include_router(visitors.router, dependencies=authenticated_user)

# Management and operational surfaces are admin-only.
app.include_router(software.router, dependencies=[Depends(require_menu_permission("software"))])
app.include_router(admin.router, dependencies=admin_only)
app.include_router(ecount_integration.router, dependencies=admin_only)
app.include_router(inventory_alerts_admin.router, dependencies=admin_only)
app.include_router(company_vehicles.router, dependencies=[Depends(require_menu_permission("company_cars"))])
app.include_router(install_files.router, dependencies=admin_only)
app.include_router(vehicle_insurance_histories.router, dependencies=[Depends(require_menu_permission("company_cars"))])
app.include_router(paju_fire_insurance.router, dependencies=[Depends(require_menu_permission("fire_insurance"))])
app.include_router(network_status.router, dependencies=[Depends(require_menu_permission("equipment_status"))])
app.include_router(network_credentials.router, dependencies=[Depends(require_menu_permission("access_info"))])
app.include_router(server_operations.router, dependencies=admin_only)
app.include_router(activity_logs.router, dependencies=[Depends(require_menu_permission("changelog"))])
app.include_router(users.router, dependencies=admin_only)
