from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routers import stats
from app.routers import assets, categories, departments, health


LOCAL_DEV_CORS_ORIGINS = [
    "http://127.0.0.1:5173",
    "http://localhost:5173",
]


def get_cors_origins() -> List[str]:
    return list(dict.fromkeys([*settings.cors_origins, *LOCAL_DEV_CORS_ORIGINS]))


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(categories.router)
app.include_router(departments.router)
app.include_router(assets.router)
app.include_router(stats.router)
