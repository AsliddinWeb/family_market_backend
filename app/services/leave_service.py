from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.leave import Leave, LeaveStatus, LeaveType
from app.schemas.leave import LeaveCreate, LeaveStatusUpdate


def calc_working_days(start: date, end: date, employee: Employee | None = None) -> int:
    """
    start..end oralig'idagi ish kunlarini hisoblaydi.
    employee berilsa — uning is_off_day() metodini ishlatadi
    (custom_off_days, custom_work_days, off_days hammasi hisobga olinadi).
    employee berilmasa — oddiy kalendar kunlari (end - start + 1).
    """
    if employee is None:
        return (end - start).days + 1

    count = 0
    current = start
    while current <= end:
        if not employee.is_off_day(current):
            count += 1
        current += timedelta(days=1)
    return count


async def get_leaves(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    status: LeaveStatus | None,
    leave_type: LeaveType | None,
) -> tuple[int, list[Leave]]:
    q = select(Leave)
    if employee_id:
        q = q.where(Leave.employee_id == employee_id)
    if status:
        q = q.where(Leave.status == status)
    if leave_type:
        q = q.where(Leave.leave_type == leave_type)
    q = q.order_by(Leave.start_date.desc())

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_leave(db: AsyncSession, leave_id: int) -> Leave | None:
    return await db.scalar(select(Leave).where(Leave.id == leave_id))


async def create_leave(db: AsyncSession, data: LeaveCreate) -> Leave:
    employee = await db.scalar(
        select(Employee).where(Employee.id == data.employee_id)
    )
    days_count = calc_working_days(data.start_date, data.end_date, employee)

    leave = Leave(**data.model_dump(), days_count=days_count)
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave


async def update_leave_status(
    db: AsyncSession,
    leave: Leave,
    data: LeaveStatusUpdate,
    approved_by_id: int,
) -> Leave:
    leave.status = data.status
    if data.rejection_reason:
        leave.rejection_reason = data.rejection_reason
    if data.status == LeaveStatus.approved:
        leave.approved_by_id = approved_by_id
        # Tasdiqlanganda days_count qayta hisoblanadi
        # (xodim off_days keyinroq o'zgargan bo'lishi mumkin)
        employee = await db.scalar(
            select(Employee).where(Employee.id == leave.employee_id)
        )
        if employee:
            leave.days_count = calc_working_days(leave.start_date, leave.end_date, employee)

    await db.commit()
    await db.refresh(leave)
    return leave


async def cancel_leave(db: AsyncSession, leave: Leave) -> Leave:
    if leave.status not in (LeaveStatus.pending, LeaveStatus.approved):
        raise ValueError("Only pending or approved leaves can be cancelled")
    leave.status = LeaveStatus.cancelled
    await db.commit()
    await db.refresh(leave)
    return leave