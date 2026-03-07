from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_hr
from app.models.attendance import AttendanceStatus
from app.models.user import User, UserRole
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceOut,
    AttendanceUpdate,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
    PaginatedAttendance,
    serialize_attendance,
)
from app.services import attendance_service

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.get("", response_model=PaginatedAttendance)
async def list_attendance(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    employee_id: int | None = Query(None),
    branch_id: int | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    status: AttendanceStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # employee roli faqat o'z davomatini ko'ra oladi
    if current_user.role == UserRole.employee:
        user_with_emp = await db.scalar(
            select(User).options(selectinload(User.employee)).where(User.id == current_user.id)
        )
        if user_with_emp and user_with_emp.employee:
            employee_id = user_with_emp.employee.id
        else:
            return PaginatedAttendance(total=0, page=page, size=size, items=[])

    total, items = await attendance_service.get_attendances(
        db, page, size, employee_id, branch_id, date_from, date_to, status
    )
    return PaginatedAttendance(
        total=total, page=page, size=size,
        items=[serialize_attendance(r) for r in items],
    )


@router.post("", response_model=AttendanceOut, status_code=201)
async def create_attendance(
    data: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    rec = await attendance_service.create_attendance(db, data)
    return serialize_attendance(rec)


@router.post("/check-in", response_model=AttendanceOut)
async def check_in(
    data: CheckInRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await attendance_service.check_in(db, data)


@router.post("/check-out", response_model=AttendanceOut)
async def check_out(
    data: CheckOutRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    try:
        return await attendance_service.check_out(db, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/summary", response_model=AttendanceSummary)
async def get_summary(
    employee_id: int = Query(...),
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # employee faqat o'zini ko'ra oladi
    if current_user.role == UserRole.employee:
        user_with_emp = await db.scalar(
            select(User).options(selectinload(User.employee)).where(User.id == current_user.id)
        )
        if user_with_emp and user_with_emp.employee:
            employee_id = user_with_emp.employee.id
        else:
            raise HTTPException(status_code=403, detail="Employee profil topilmadi")
    return await attendance_service.get_summary(db, employee_id, year, month)


@router.get("/{attendance_id}", response_model=AttendanceOut)
async def get_attendance(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    record = await attendance_service.get_attendance(db, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return record


@router.patch("/{attendance_id}", response_model=AttendanceOut)
async def update_attendance(
    attendance_id: int,
    data: AttendanceUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    record = await attendance_service.get_attendance(db, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    return await attendance_service.update_attendance(db, record, data)


@router.delete("/{attendance_id}", status_code=204)
async def delete_attendance(
    attendance_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    record = await attendance_service.get_attendance(db, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance not found")
    await attendance_service.delete_attendance(db, record)