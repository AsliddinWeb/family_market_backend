from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# noqa: F401 — ensure all mappers are registered before first query
import app.models  # noqa: F401

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.routers import (
    auth, branches, departments, employees,
    attendance, salary, bonuses, deductions,
    kpi, leaves, dashboard, telegram,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="FamilyMarket HR API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/media", StaticFiles(directory=settings.MEDIA_DIR), name="media")

register_exception_handlers(app)

# Routers
app.include_router(auth.router)
app.include_router(branches.router)
app.include_router(departments.router)
app.include_router(employees.router)
app.include_router(attendance.router)
app.include_router(salary.router)
app.include_router(bonuses.router)
app.include_router(deductions.router)
app.include_router(kpi.router)
app.include_router(leaves.router)
app.include_router(dashboard.router)
app.include_router(telegram.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}