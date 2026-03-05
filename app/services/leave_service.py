from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leave import Leave, LeaveStatus, LeaveType
from app.schemas.leave import LeaveCreate, LeaveStatusUpdate


def _calc_days(start: date, end: date) -> int:
    return (end - start).days + 1


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
    leave = Leave(
        **data.model_dump(),
        days_count=_calc_days(data.start_date, data.end_date),
    )
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