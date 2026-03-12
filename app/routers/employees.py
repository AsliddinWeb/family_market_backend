import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_admin, get_current_user, get_hr
from app.core.config import settings
from app.models.employee import Employee as EmployeeModel
from app.models.user import User, User as UserModel
from app.schemas.employee import (
    EmployeeCreate, EmployeeDetail, EmployeeOut,
    EmployeeUpdate, PaginatedEmployees,
)
from app.services import employee_service

router = APIRouter(prefix="/api/employees", tags=["Employees"])


@router.get("", response_model=PaginatedEmployees)
async def list_employees(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    branch_id: int | None = Query(None),
    department_id: int | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    total, items = await employee_service.get_employees(
        db, page, size, branch_id, department_id, is_active, search
    )
    return PaginatedEmployees(
        total=total,
        page=page,
        size=size,
        items=[_to_out(emp) for emp in items],
    )


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(
    data: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    existing_user = await db.scalar(
        select(UserModel).where(UserModel.phone == data.phone)
    )
    if existing_user:
        raise HTTPException(status_code=400, detail="Bu phone raqam allaqachon mavjud")

    if data.telegram_user_id:
        existing_tg = await db.scalar(
            select(EmployeeModel).where(
                EmployeeModel.telegram_user_id == data.telegram_user_id
            )
        )
        if existing_tg:
            raise HTTPException(status_code=400, detail="Bu Telegram ID allaqachon mavjud")

    emp = await employee_service.create_employee(db, data)
    emp = await employee_service.get_employee(db, emp.id)
    return _to_out(emp)


@router.get("/me", response_model=EmployeeDetail)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = await db.scalar(
        select(EmployeeModel)
        .options(
            selectinload(EmployeeModel.user),
            selectinload(EmployeeModel.branch),
            selectinload(EmployeeModel.department),
        )
        .where(EmployeeModel.user_id == current_user.id, EmployeeModel.is_deleted == False)
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return _to_detail(emp)


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    emp = await employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    return _to_detail(emp)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: int,
    data: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    emp = await employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    updated = await employee_service.update_employee(db, emp, data)
    updated = await employee_service.get_employee(db, updated.id)
    return _to_out(updated)


@router.post("/{employee_id}/photo", response_model=EmployeeOut)
async def upload_photo(
    employee_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    emp = await employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Faqat JPEG, PNG yoki WebP ruxsat etiladi")

    ext      = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
    filename = f"employees/{employee_id}_{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(settings.MEDIA_DIR, filename)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Eski rasmni o'chirish
    if emp.photo:
        old_path = os.path.join(settings.MEDIA_DIR, emp.photo)
        if os.path.exists(old_path):
            os.remove(old_path)

    emp.photo = filename
    await db.commit()
    await db.refresh(emp)
    emp = await employee_service.get_employee(db, emp.id)
    return _to_out(emp)


@router.delete("/{employee_id}", status_code=204)
async def delete_employee(
    employee_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin),
):
    emp = await employee_service.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")
    await employee_service.delete_employee(db, emp)


# ── Helpers ──────────────────────────────────────────────────

def _to_out(emp) -> dict:
    return {
        "id":                 emp.id,
        "user_id":            emp.user_id,
        "full_name":          emp.user.full_name,
        "phone":              emp.user.phone,
        "role":               emp.user.role,
        "branch_id":          emp.branch_id,
        "branch": {
            "id":        emp.branch.id,
            "name":      emp.branch.name,
            "is_active": emp.branch.is_active,
        } if emp.branch else None,
        "department_id": emp.department_id,
        "department": {
            "id":        emp.department.id,
            "name":      emp.department.name,
            "branch_id": emp.department.branch_id,
            "is_active": emp.department.is_active,
        } if emp.department else None,
        "position":           emp.position,
        "employment_type":    emp.employment_type,
        "hire_date":          str(emp.hire_date) if emp.hire_date else None,
        "base_salary":        emp.base_salary,
        "hourly_rate":        emp.hourly_rate,
        "work_hours_per_day": emp.work_hours_per_day,
        "off_days":           emp.off_days,
        "telegram_user_id":   emp.telegram_user_id,
        "photo":              emp.photo,
        "face_photo":         emp.face_photo,
        "is_active":          emp.is_active,
    }


def _to_detail(emp) -> dict:
    return {
        **_to_out(emp),
        "branch":     emp.branch,
        "department": emp.department,
    }