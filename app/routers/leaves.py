from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_hr
from app.models.leave import LeaveStatus, LeaveType
from app.models.user import User, UserRole
from app.schemas.leave import LeaveCreate, LeaveOut, LeaveStatusUpdate, PaginatedLeaves
from app.services import leave_service

router = APIRouter(prefix="/api/leaves", tags=["Leaves"])


@router.get("", response_model=PaginatedLeaves)
async def list_leaves(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    status: LeaveStatus | None = Query(None),
    leave_type: LeaveType | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # employee faqat o'z ta'tillarini ko'ra oladi
    if current_user.role == UserRole.employee:
        user_with_emp = await db.scalar(
            select(User).options(selectinload(User.employee)).where(User.id == current_user.id)
        )
        if user_with_emp and user_with_emp.employee:
            employee_id = user_with_emp.employee.id
        else:
            return PaginatedLeaves(total=0, page=page, size=size, items=[])

    total, items = await leave_service.get_leaves(
        db, page, size, employee_id, status, leave_type
    )
    return PaginatedLeaves(total=total, page=page, size=size, items=items)


@router.post("", response_model=LeaveOut, status_code=201)
async def create_leave(
    data: LeaveCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await leave_service.create_leave(db, data)


@router.get("/{leave_id}", response_model=LeaveOut)
async def get_leave(
    leave_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    leave = await leave_service.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return leave


@router.patch("/{leave_id}/status", response_model=LeaveOut)
async def update_status(
    leave_id: int,
    data: LeaveStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_hr),
):
    leave = await leave_service.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    return await leave_service.update_leave_status(db, leave, data, current_user.id)


@router.patch("/{leave_id}/cancel", response_model=LeaveOut)
async def cancel_leave(
    leave_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    leave = await leave_service.get_leave(db, leave_id)
    if not leave:
        raise HTTPException(status_code=404, detail="Leave not found")
    try:
        return await leave_service.cancel_leave(db, leave)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))