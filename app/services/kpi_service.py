from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kpi import KPI, KPITemplate
from app.schemas.kpi import KPICreate, KPIUpdate, KPISummary, KPITemplateCreate, KPITemplateUpdate


async def get_kpis(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    year: int | None,
    month: int | None,
) -> tuple[int, list[KPI]]:
    q = select(KPI)
    if employee_id:
        q = q.where(KPI.employee_id == employee_id)
    if year:
        q = q.where(KPI.period_year == year)
    if month:
        q = q.where(KPI.period_month == month)
    q = q.order_by(KPI.period_year.desc(), KPI.period_month.desc())

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_kpi(db: AsyncSession, kpi_id: int) -> KPI | None:
    return await db.scalar(select(KPI).where(KPI.id == kpi_id))


async def create_kpi(db: AsyncSession, data: KPICreate) -> KPI:
    kpi = KPI(**data.model_dump())
    db.add(kpi)
    await db.commit()
    await db.refresh(kpi)
    return kpi


async def update_kpi(db: AsyncSession, kpi: KPI, data: KPIUpdate) -> KPI:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(kpi, field, value)
    await db.commit()
    await db.refresh(kpi)
    return kpi


async def delete_kpi(db: AsyncSession, kpi: KPI) -> None:
    await db.delete(kpi)
    await db.commit()


async def get_kpi_summary(
    db: AsyncSession, employee_id: int, year: int, month: int
) -> KPISummary:
    kpis = (await db.execute(
        select(KPI).where(
            KPI.employee_id == employee_id,
            KPI.period_year == year,
            KPI.period_month == month,
        )
    )).scalars().all()

    total_score = 0.0
    max_score = 0.0
    for k in kpis:
        max_score += k.weight
        if k.target_value > 0:
            total_score += (k.actual_value / k.target_value) * k.weight

    percentage = round((total_score / max_score * 100) if max_score > 0 else 0, 2)

    return KPISummary(
        employee_id=employee_id,
        period_year=year,
        period_month=month,
        total_score=round(total_score, 2),
        max_score=round(max_score, 2),
        percentage=percentage,
        kpi_count=len(kpis),
    )


# ── KPITemplate ──────────────────────────────────────────────

async def get_templates(
    db: AsyncSession,
    page: int,
    size: int,
    department_id: int | None,
    is_active: bool | None,
) -> tuple[int, list[KPITemplate]]:
    q = select(KPITemplate)
    if department_id is not None:
        q = q.where(KPITemplate.department_id == department_id)
    if is_active is not None:
        q = q.where(KPITemplate.is_active == is_active)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def create_template(db: AsyncSession, data: KPITemplateCreate) -> KPITemplate:
    template = KPITemplate(**data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession, template: KPITemplate, data: KPITemplateUpdate
) -> KPITemplate:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(template, field, value)
    await db.commit()
    await db.refresh(template)
    return template