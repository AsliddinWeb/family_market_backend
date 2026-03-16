from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin, get_current_user, get_hr
from app.models.employee import Employee
from app.models.salary import SalaryStatus
from app.models.user import User
from app.schemas.salary import (
    PaginatedSalaryRecords,
    SalaryRecordCreate,
    SalaryRecordOut,
    SalaryStatusUpdate,
)
from app.services import salary_service

router = APIRouter(prefix="/api/salary", tags=["Salary"])


@router.get("", response_model=PaginatedSalaryRecords)
async def list_salary_records(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    status: SalaryStatus | None = Query(None),
    branch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    total, items = await salary_service.get_salary_records(
        db, page, size, employee_id, year, month, status, branch_id
    )
    return PaginatedSalaryRecords(
        total=total, page=page, size=size,
        items=[SalaryRecordOut.from_orm_with_net(i) for i in items]
    )


@router.post("", response_model=SalaryRecordOut, status_code=201)
async def create_salary_record(
    data: SalaryRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_hr),
):
    try:
        record = await salary_service.create_salary_record(db, data, current_user.id)
        loaded = await salary_service.get_salary_record(db, record.id)
        return SalaryRecordOut.from_orm_with_net(loaded)
    except ValueError as e:
        msg = str(e)
        status_code = 409 if "already exists" in msg else 400
        raise HTTPException(status_code=status_code, detail=msg)


# ── /my — xodim o'z oyligini ko'radi ─────────────────────────────────────────
# batch-status va daily-earnings kabi — /{record_id} dan OLDIN turishi shart

@router.get("/my", response_model=PaginatedSalaryRecords)
async def my_salary_records(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=24),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xodimning o'z oylik yozuvlari — barcha rollar uchun ochiq."""
    emp = await db.scalar(
        select(Employee)
        .options(selectinload(Employee.user))
        .where(Employee.user_id == current_user.id)
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    total, items = await salary_service.get_salary_records(
        db, page, size, emp.id, year, month, None
    )
    return PaginatedSalaryRecords(
        total=total, page=page, size=size,
        items=[SalaryRecordOut.from_orm_with_net(i) for i in items]
    )


# ── batch-status ──────────────────────────────────────────────────────────────

class BatchStatusUpdate(BaseModel):
    ids: list[int]
    status: SalaryStatus


@router.post("/batch-status", response_model=dict)
async def batch_update_salary_status(
    data: BatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    """Bir nechta oylikni bir vaqtda tasdiqlash yoki to'lash."""
    ok, fail = 0, 0
    for record_id in data.ids:
        record = await salary_service.get_salary_record(db, record_id)
        if not record:
            fail += 1
            continue
        try:
            await salary_service.update_salary_status(
                db, record, SalaryStatusUpdate(status=data.status)
            )
            ok += 1
        except Exception:
            fail += 1
    return {"ok": ok, "fail": fail}


@router.get("/daily-earnings/{employee_id}")
async def get_daily_earnings(
    employee_id: int,
    year: int = Query(..., ge=2020, le=2100),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    try:
        return await salary_service.get_daily_earnings(db, employee_id, year, month)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{record_id}", response_model=SalaryRecordOut)
async def get_salary_record(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    record = await salary_service.get_salary_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Salary record not found")
    return SalaryRecordOut.from_orm_with_net(record)


@router.patch("/{record_id}/status", response_model=SalaryRecordOut)
async def update_salary_status(
    record_id: int,
    data: SalaryStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    record = await salary_service.get_salary_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Salary record not found")
    await salary_service.update_salary_status(db, record, data)
    updated = await salary_service.get_salary_record(db, record_id)
    return SalaryRecordOut.from_orm_with_net(updated)