from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin, get_hr
from app.models.user import User
from app.schemas.salary import BonusCreate, BonusOut, PaginatedBonuses
from app.services import salary_service

router = APIRouter(prefix="/api/bonuses", tags=["Bonuses"])


@router.get("", response_model=PaginatedBonuses)
async def list_bonuses(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    total, items = await salary_service.get_bonuses(db, page, size, employee_id, year, month)
    return PaginatedBonuses(total=total, page=page, size=size, items=items)


@router.post("", response_model=BonusOut, status_code=201)
async def create_bonus(
    data: BonusCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_hr),
):
    return await salary_service.create_bonus(db, data, current_user.id)


@router.delete("/{bonus_id}", status_code=204)
async def delete_bonus(
    bonus_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    bonus = await salary_service.get_bonuses(db, 1, 1, None, None, None)
    from sqlalchemy import select
    from app.models.salary import Bonus
    from app.core.database import get_db
    b = await db.get(Bonus, bonus_id)
    if not b:
        raise HTTPException(status_code=404, detail="Bonus not found")
    await salary_service.delete_bonus(db, b)