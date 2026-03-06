from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TZ
from app.core.database import get_db

from app.core.dependencies import get_hr
from app.models.attendance import Attendance, AttendanceStatus
from app.models.employee import Employee
from app.models.leave import Leave, LeaveStatus
from app.models.salary import SalaryRecord, SalaryStatus
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


class DashboardStats(BaseModel):
    total_employees: int
    active_employees: int
    today_present: int
    today_absent: int
    today_late: int
    pending_leaves: int
    draft_salaries: int
    paid_salaries_this_month: int


@router.get("", response_model=DashboardStats)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_hr),
):
    now = datetime.now(tz=TZ)
    today = now.date()
    current_year = now.year
    current_month = now.month

    total_employees = await db.scalar(
        select(func.count(Employee.id)).where(Employee.is_deleted == False)
    )
    active_employees = await db.scalar(
        select(func.count(Employee.id)).where(
            Employee.is_deleted == False, Employee.is_active == True
        )
    )
    today_present = await db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.present,
        )
    )
    today_late = await db.scalar(
        select(func.count(Attendance.id)).where(
            Attendance.date == today,
            Attendance.status == AttendanceStatus.late,
        )
    )
    today_total_marked = await db.scalar(
        select(func.count(Attendance.id)).where(Attendance.date == today)
    )
    today_absent = (active_employees or 0) - (today_total_marked or 0)

    pending_leaves = await db.scalar(
        select(func.count(Leave.id)).where(Leave.status == LeaveStatus.pending)
    )
    draft_salaries = await db.scalar(
        select(func.count(SalaryRecord.id)).where(SalaryRecord.status == SalaryStatus.draft)
    )
    paid_salaries_this_month = await db.scalar(
        select(func.count(SalaryRecord.id)).where(
            SalaryRecord.status == SalaryStatus.paid,
            SalaryRecord.period_year == current_year,
            SalaryRecord.period_month == current_month,
        )
    )

    return DashboardStats(
        total_employees=total_employees or 0,
        active_employees=active_employees or 0,
        today_present=today_present or 0,
        today_absent=max(today_absent, 0),
        today_late=today_late or 0,
        pending_leaves=pending_leaves or 0,
        draft_salaries=draft_salaries or 0,
        paid_salaries_this_month=paid_salaries_this_month or 0,
    )