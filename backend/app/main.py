import logging
from typing import List
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.auth import get_current_user, require_admin, require_authenticated_access
from app.core.config import REQUIRED_CORS_ORIGINS, settings
from app.api.routers import (
    activity_logs,
    admin,
    auth,
    beverage_orders,
    company_vehicles,
    dashboard_notices,
    install_files,
    network_credentials,
    network_status,
    paju_fire_insurance,
    server_operations,
    software,
    stats,
    users,
    vendor_contacts,
    vehicle_insurance_histories,
    visitors,
    work_manuals,
)
from app.routers import assets, categories, departments, health


def get_cors_origins() -> List[str]:
    # Required origins remain available when CORS_ORIGINS is missing or empty
    # in the NAS environment. Explicit env origins may safely add entries.
    return list(
        dict.fromkeys([*settings.cors_origin_list, *REQUIRED_CORS_ORIGINS])
    )


app = FastAPI(title=settings.app_name)
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
)

Path(settings.upload_dir).resolve().mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads",
    StaticFiles(directory=str(Path(settings.upload_dir).resolve())),
    name="uploads",
)

app.include_router(health.router)
app.include_router(auth.router)

authenticated_access = [Depends(require_authenticated_access)]
authenticated_user = [Depends(get_current_user)]
admin_only = [Depends(require_admin)]

# User-facing read routes. Non-safe methods require the admin role.
app.include_router(categories.router, dependencies=authenticated_access)
app.include_router(departments.router, dependencies=authenticated_access)
app.include_router(assets.router, dependencies=authenticated_access)
app.include_router(stats.router, dependencies=authenticated_access)
app.include_router(beverage_orders.router, dependencies=authenticated_access)
app.include_router(dashboard_notices.router, dependencies=authenticated_access)
app.include_router(work_manuals.router, dependencies=authenticated_access)
app.include_router(vendor_contacts.router, dependencies=authenticated_access)
app.include_router(visitors.router, dependencies=authenticated_user)

# Management and operational surfaces are admin-only.
app.include_router(software.router, dependencies=admin_only)
app.include_router(admin.router, dependencies=admin_only)
app.include_router(company_vehicles.router, dependencies=admin_only)
app.include_router(install_files.router, dependencies=admin_only)
app.include_router(vehicle_insurance_histories.router, dependencies=admin_only)
app.include_router(paju_fire_insurance.router, dependencies=admin_only)
app.include_router(network_status.router, dependencies=admin_only)
app.include_router(network_credentials.router, dependencies=admin_only)
app.include_router(server_operations.router, dependencies=admin_only)
app.include_router(activity_logs.router, dependencies=admin_only)
app.include_router(users.router, dependencies=admin_only)
