from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_admin, get_current_user, get_hr
from app.models.user import User
from app.schemas.branch import (
    DepartmentCreate, DepartmentOut, DepartmentUpdate,
    PaginatedDepartments,
)
from app.services import branch_service

router = APIRouter(prefix="/api/departments", tags=["Departments"])


@router.get("", response_model=PaginatedDepartments)
async def list_departments(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    branch_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    total, items = await branch_service.get_departments(
        db, page, size, branch_id, is_active, search
    )
    return PaginatedDepartments(total=total, page=page, size=size, items=items)


@router.post("", response_model=DepartmentOut, status_code=201)
async def create_department(
    data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    # branch mavjudligini tekshirish
    branch = await branch_service.get_branch(db, data.branch_id)
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    return await branch_service.create_department(db, data)


@router.get("/{dept_id}", response_model=DepartmentOut)
async def get_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    dept = await branch_service.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return dept


@router.patch("/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    dept = await branch_service.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    return await branch_service.update_department(db, dept, data)


@router.delete("/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    dept = await branch_service.get_department(db, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await branch_service.delete_department(db, dept)