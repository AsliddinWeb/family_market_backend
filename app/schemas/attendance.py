from datetime import date, time
from typing import Any

from pydantic import BaseModel

from app.models.attendance import AttendanceSource, AttendanceStatus
from app.schemas.branch import BranchShort


class EmployeeShort(BaseModel):
    id: int
    full_name: str
    phone: str
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


class CheckInRequest(BaseModel):
    """Telegram bot orqali check-in"""
    employee_id: int
    check_in_time: time
    check_in_photo: str | None = None
    check_in_location: dict[str, Any] | None = None


class CheckOutRequest(BaseModel):
    """Telegram bot orqali check-out"""
    employee_id: int
    check_out_time: time
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