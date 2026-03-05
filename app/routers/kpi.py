from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_hr
from app.models.user import User
from app.schemas.kpi import (
    KPICreate, KPIOut, KPIUpdate, KPISummary,
    KPITemplateCreate, KPITemplateOut, KPITemplateUpdate,
    PaginatedKPI,
)
from app.services import kpi_service

router = APIRouter(prefix="/api/kpi", tags=["KPI"])


@router.get("", response_model=PaginatedKPI)
async def list_kpis(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    total, items = await kpi_service.get_kpis(db, page, size, employee_id, year, month)
    return PaginatedKPI(
        total=total, page=page, size=size,
        items=[KPIOut.from_orm_with_score(i) for i in items]
    )


@router.post("", response_model=KPIOut, status_code=201)
async def create_kpi(
    data: KPICreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    kpi = await kpi_service.create_kpi(db, data)
    return KPIOut.from_orm_with_score(kpi)


@router.get("/summary", response_model=KPISummary)
async def get_summary(
    employee_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    return await kpi_service.get_kpi_summary(db, employee_id, year, month)


@router.get("/{kpi_id}", response_model=KPIOut)
async def get_kpi(
    kpi_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    kpi = await kpi_service.get_kpi(db, kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    return KPIOut.from_orm_with_score(kpi)


@router.patch("/{kpi_id}", response_model=KPIOut)
async def update_kpi(
    kpi_id: int,
    data: KPIUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    kpi = await kpi_service.get_kpi(db, kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    updated = await kpi_service.update_kpi(db, kpi, data)
    return KPIOut.from_orm_with_score(updated)


@router.delete("/{kpi_id}", status_code=204)
async def delete_kpi(
    kpi_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    kpi = await kpi_service.get_kpi(db, kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI not found")
    await kpi_service.delete_kpi(db, kpi)


# ── Templates ────────────────────────────────────────────────

@router.get("/templates/list", response_model=list[KPITemplateOut])
async def list_templates(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    department_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    _, items = await kpi_service.get_templates(db, page, size, department_id, is_active)
    return items


@router.post("/templates", response_model=KPITemplateOut, status_code=201)
async def create_template(
    data: KPITemplateCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    return await kpi_service.create_template(db, data)


@router.patch("/templates/{template_id}", response_model=KPITemplateOut)
async def update_template(
    template_id: int,
    data: KPITemplateUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    from app.models.kpi import KPITemplate
    template = await db.get(KPITemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return await kpi_service.update_template(db, template, data)