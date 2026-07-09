from typing import List
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routers import (
    activity_logs,
    admin,
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
    vendor_contacts,
    vehicle_insurance_histories,
    visitors,
    work_manuals,
)
from app.routers import assets, categories, departments, health


LOCAL_DEV_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:3010",
]


def get_cors_origins() -> List[str]:
    return list(dict.fromkeys([*settings.cors_origin_list, *LOCAL_DEV_CORS_ORIGINS]))


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
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
app.include_router(categories.router)
app.include_router(departments.router)
app.include_router(assets.router)
app.include_router(stats.router)
app.include_router(software.router)
app.include_router(admin.router)
app.include_router(beverage_orders.router)
app.include_router(company_vehicles.router)
app.include_router(dashboard_notices.router)
app.include_router(install_files.router)
app.include_router(vehicle_insurance_histories.router)
app.include_router(paju_fire_insurance.router)
app.include_router(network_status.router)
app.include_router(network_credentials.router)
app.include_router(server_operations.router)
app.include_router(visitors.router)
app.include_router(activity_logs.router)
app.include_router(work_manuals.router)
app.include_router(vendor_contacts.router)
