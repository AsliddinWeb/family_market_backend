from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin, get_hr
from app.models.user import User
from app.schemas.salary import DeductionCreate, DeductionOut, PaginatedDeductions
from app.services import salary_service

router = APIRouter(prefix="/api/deductions", tags=["Deductions"])


@router.get("", response_model=PaginatedDeductions)
async def list_deductions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    total, items = await salary_service.get_deductions(db, page, size, employee_id, year, month)
    return PaginatedDeductions(total=total, page=page, size=size, items=items)


@router.post("", response_model=DeductionOut, status_code=201)
async def create_deduction(
    data: DeductionCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    return await salary_service.create_deduction(db, data)


@router.delete("/{deduction_id}", status_code=204)
async def delete_deduction(
    deduction_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    from app.models.salary import Deduction
    d = await db.get(Deduction, deduction_id)
    if not d:
        raise HTTPException(status_code=404, detail="Deduction not found")
    await salary_service.delete_deduction(db, d)