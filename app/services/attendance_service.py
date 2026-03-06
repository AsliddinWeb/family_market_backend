from calendar import monthrange
from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import TZ
from app.models.attendance import Attendance, AttendanceSource, AttendanceStatus
from app.models.employee import Employee
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceSummary,
    CheckInRequest,
    CheckOutRequest,
)


async def get_attendances(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    branch_id: int | None,
    date_from,
    date_to,
    status: AttendanceStatus | None,
) -> tuple[int, list[Attendance]]:
    q = select(Attendance).options(selectinload(Attendance.employee))

    if employee_id:
        q = q.where(Attendance.employee_id == employee_id)
    if branch_id:
        q = q.join(Attendance.employee).where(Employee.branch_id == branch_id)
    if date_from:
        q = q.where(Attendance.date >= date_from)
    if date_to:
        q = q.where(Attendance.date <= date_to)
    if status:
        q = q.where(Attendance.status == status)

    q = q.order_by(Attendance.date.desc())

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_attendance(db: AsyncSession, attendance_id: int) -> Attendance | None:
    return await db.scalar(
        select(Attendance).where(Attendance.id == attendance_id)
    )


async def get_by_employee_date(db: AsyncSession, employee_id: int, d) -> Attendance | None:
    return await db.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.date == d,
        )
    )


async def create_attendance(db: AsyncSession, data: AttendanceCreate) -> Attendance:
    record = Attendance(**data.model_dump())
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def update_attendance(
    db: AsyncSession, record: Attendance, data: AttendanceUpdate
) -> Attendance:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(record, field, value)
    await db.commit()
    await db.refresh(record)
    return record


async def delete_attendance(db: AsyncSession, record: Attendance) -> None:
    await db.delete(record)
    await db.commit()


async def check_in(db: AsyncSession, data: CheckInRequest) -> Attendance:
    today = datetime.now(tz=TZ).date()
    record = await get_by_employee_date(db, data.employee_id, today)

    late_minutes = 0
    employee = await db.scalar(
        select(Employee).options(selectinload(Employee.branch))
        .where(Employee.id == data.employee_id)
    )
    if employee and employee.branch:
        work_start: time = employee.branch.work_start_time
        ci: time = data.check_in_time
        if ci > work_start:
            late_minutes = (ci.hour * 60 + ci.minute) - (work_start.hour * 60 + work_start.minute)

    status = AttendanceStatus.late if late_minutes > 0 else AttendanceStatus.present

    if record:
        record.check_in_time = data.check_in_time
        record.check_in_photo = data.check_in_photo
        record.check_in_location = data.check_in_location
        record.late_minutes = late_minutes
        record.status = status
        record.source = AttendanceSource.telegram
    else:
        record = Attendance(
            employee_id=data.employee_id,
            date=today,
            check_in_time=data.check_in_time,
            check_in_photo=data.check_in_photo,
            check_in_location=data.check_in_location,
            late_minutes=late_minutes,
            status=status,
            source=AttendanceSource.telegram,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return record


async def check_out(db: AsyncSession, data: CheckOutRequest) -> Attendance:
    today = datetime.now(tz=TZ).date()
    record = await get_by_employee_date(db, data.employee_id, today)
    if not record:
        raise ValueError("Check-in topilmadi")

    record.check_out_time = data.check_out_time
    record.check_out_photo = data.check_out_photo
    record.check_out_location = data.check_out_location
    await db.commit()
    await db.refresh(record)
    return record


async def get_summary(
    db: AsyncSession,
    employee_id: int,
    year: int,
    month: int,
) -> AttendanceSummary:
    from datetime import date as date_type

    first_day = date_type(year, month, 1)
    last_day = date_type(year, month, monthrange(year, month)[1])

    records = (await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            Attendance.date >= first_day,
            Attendance.date <= last_day,
        )
    )).scalars().all()

    counts = {s: 0 for s in AttendanceStatus}
    total_late = 0
    for r in records:
        counts[r.status] += 1
        total_late += r.late_minutes

    return AttendanceSummary(
        employee_id=employee_id,
        total_days=len(records),
        present=counts[AttendanceStatus.present],
        absent=counts[AttendanceStatus.absent],
        late=counts[AttendanceStatus.late],
        half_day=counts[AttendanceStatus.half_day],
        holiday=counts[AttendanceStatus.holiday],
        total_late_minutes=total_late,
    )