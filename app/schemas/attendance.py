from datetime import date, time
from typing import Any

from pydantic import BaseModel

from app.models.attendance import AttendanceSource, AttendanceStatus
from app.schemas.branch import BranchShort


class EmployeeShort(BaseModel):
    id: int
    full_name: str = ""
    phone: str = ""
    branch_id: int | None = None
    branch: BranchShort | None = None

    model_config = {"from_attributes": True}


class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    check_in_time: time | None = None
    check_out_time: time | None = None
    check_in_photo: str | None = None
    check_out_photo: str | None = None
    check_in_location: dict[str, Any] | None = None
    check_out_location: dict[str, Any] | None = None
    status: AttendanceStatus = AttendanceStatus.present
    late_minutes: int = 0
    source: AttendanceSource = AttendanceSource.manual
    notes: str | None = None


class AttendanceUpdate(BaseModel):
    check_in_time: time | None = None
    check_out_time: time | None = None
    check_in_photo: str | None = None
    check_out_photo: str | None = None
    check_in_location: dict[str, Any] | None = None
    check_out_location: dict[str, Any] | None = None
    status: AttendanceStatus | None = None
    late_minutes: int | None = None
    notes: str | None = None


class AttendanceOut(BaseModel):
    id: int
    employee_id: int
    date: date
    check_in_time: time | None
    check_out_time: time | None
    check_in_photo: str | None
    check_out_photo: str | None
    check_in_location: dict[str, Any] | None
    check_out_location: dict[str, Any] | None
    status: AttendanceStatus
    late_minutes: int
    source: AttendanceSource
    notes: str | None
    employee: EmployeeShort | None = None

    model_config = {"from_attributes": True}


def serialize_attendance(rec) -> AttendanceOut:
    """ORM Attendance -> AttendanceOut, user.full_name ni to'g'ri olish uchun"""
    emp_data = None
    if rec.employee is not None:
        emp = rec.employee
        emp_data = EmployeeShort(
            id=emp.id,
            full_name=emp.user.full_name if (emp.user) else "",
            phone=emp.user.phone if (emp.user) else "",
            branch_id=emp.branch_id,
            branch=BranchShort.model_validate(emp.branch) if emp.branch else None,
        )
    return AttendanceOut(
        id=rec.id,
        employee_id=rec.employee_id,
        date=rec.date,
        check_in_time=rec.check_in_time,
        check_out_time=rec.check_out_time,
        check_in_photo=rec.check_in_photo,
        check_out_photo=rec.check_out_photo,
        check_in_location=rec.check_in_location,
        check_out_location=rec.check_out_location,
        status=rec.status,
        late_minutes=rec.late_minutes,
        source=rec.source,
        notes=rec.notes,
        employee=emp_data,
    )


class CheckInRequest(BaseModel):
    """Telegram bot / Kabinet orqali check-in"""
    employee_id: int
    check_in_time: time | None = None   # None bo'lsa backend TZ vaqtini ishlatadi
    check_in_photo: str | None = None
    check_in_location: dict[str, Any] | None = None


class CheckOutRequest(BaseModel):
    """Telegram bot / Kabinet orqali check-out"""
    employee_id: int
    check_out_time: time | None = None  # None bo'lsa backend TZ vaqtini ishlatadi
    check_out_photo: str | None = None
    check_out_location: dict[str, Any] | None = None


class PaginatedAttendance(BaseModel):
    total: int
    page: int
    size: int
    items: list[AttendanceOut]


class AttendanceSummary(BaseModel):
    """Oylik yoki haftalik statistika"""
    employee_id: int
    total_days: int
    present: int
    absent: int
    late: int
    half_day: int
    holiday: int
    total_late_minutes: int