from calendar import monthrange
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee import Employee
from app.models.salary import Bonus, Deduction, DeductionType, SalaryRecord, SalaryStatus
from app.schemas.salary import (
    BonusCreate,
    DeductionCreate,
    SalaryRecordCreate,
    SalaryStatusUpdate,
)

WEEKDAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ── SalaryRecord ─────────────────────────────────────────────

async def get_salary_records(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    year: int | None,
    month: int | None,
    status: SalaryStatus | None,
    branch_id: int | None = None,
) -> tuple[int, list[SalaryRecord]]:

    q = (
        select(SalaryRecord)
        .join(Employee, SalaryRecord.employee_id == Employee.id)
        .options(selectinload(SalaryRecord.employee).selectinload(Employee.user))
    )

    if employee_id:
        q = q.where(SalaryRecord.employee_id == employee_id)
    if branch_id:
        q = q.where(Employee.branch_id == branch_id)
    if year:
        q = q.where(SalaryRecord.period_year == year)
    if month:
        q = q.where(SalaryRecord.period_month == month)
    if status:
        q = q.where(SalaryRecord.status == status)

    q = q.order_by(SalaryRecord.period_year.desc(), SalaryRecord.period_month.desc())

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def get_salary_record(db: AsyncSession, record_id: int) -> SalaryRecord | None:
    return await db.scalar(
        select(SalaryRecord)
        .where(SalaryRecord.id == record_id)
        .options(selectinload(SalaryRecord.employee).selectinload(Employee.user))
    )




async def create_salary_record(
    db: AsyncSession, data: SalaryRecordCreate, created_by_id: int
) -> SalaryRecord:
    from app.models.attendance import Attendance
    from app.models.leave import Leave, LeaveStatus, LeaveType

    employee = await db.scalar(select(Employee).where(Employee.id == data.employee_id))
    if not employee:
        raise ValueError("Employee not found")

    emp_base_salary = employee.base_salary
    emp_hourly_rate = employee.hourly_rate
    emp_work_hours = employee.work_hours_per_day or 8
    emp_off_days: list[str] = employee.off_days or []

    existing = await db.scalar(
        select(SalaryRecord).where(
            SalaryRecord.employee_id == data.employee_id,
            SalaryRecord.period_year == data.period_year,
            SalaryRecord.period_month == data.period_month,
        )
    )
    if existing:
        raise ValueError("Salary record already exists for this period")

    year = data.period_year
    month = data.period_month

    hourly_rate = _calc_hourly_rate(
        emp_base_salary, emp_hourly_rate, emp_work_hours, emp_off_days, year, month
    )
    daily_wage = (hourly_rate * Decimal(emp_work_hours)).quantize(Decimal("1"))

    _, days_in_month = monthrange(year, month)
    period_start = date(year, month, 1)
    period_end = date(year, month, days_in_month)

    unpaid_leaves = (await db.execute(
        select(Leave).where(
            Leave.employee_id == data.employee_id,
            Leave.leave_type == LeaveType.unpaid,
            Leave.status == LeaveStatus.approved,
            Leave.start_date <= period_end,
            Leave.end_date >= period_start,
        )
    )).scalars().all()

    unpaid_days = Decimal("0")
    for lv in unpaid_leaves:
        overlap_start = max(lv.start_date, period_start)
        overlap_end = min(lv.end_date, period_end)
        days = (overlap_end - overlap_start).days + 1
        if days > 0:
            unpaid_days += Decimal(days)

    leave_deduction_from_leaves = (unpaid_days * daily_wage).quantize(Decimal("1"))

    today = date.today()
    attendances = (await db.execute(
        select(Attendance).where(
            Attendance.employee_id == data.employee_id,
            func.extract("year", Attendance.date) == year,
            func.extract("month", Attendance.date) == month,
        )
    )).scalars().all()

    no_checkout_days = sum(
        1 for a in attendances
        if a.check_in_time and not a.check_out_time and a.date < today
    )
    leave_deduction_from_attendance = (Decimal(no_checkout_days) * daily_wage).quantize(Decimal("1"))

    old_auto = (await db.execute(
        select(Deduction).where(
            Deduction.employee_id == data.employee_id,
            Deduction.period_year == year,
            Deduction.period_month == month,
            Deduction.auto_generated == True,
        )
    )).scalars().all()
    for d in old_auto:
        await db.delete(d)

    if leave_deduction_from_leaves > 0:
        db.add(Deduction(
            employee_id=data.employee_id,
            amount=leave_deduction_from_leaves,
            reason=f"Haqsiz ta'til ({int(unpaid_days)} kun x {formatMoney_py(daily_wage)})",
            deduction_type=DeductionType.absence,
            period_year=year,
            period_month=month,
            auto_generated=True,
        ))

    if leave_deduction_from_attendance > 0:
        db.add(Deduction(
            employee_id=data.employee_id,
            amount=leave_deduction_from_attendance,
            reason=f"Check-out qilinmagan ({no_checkout_days} kun x {formatMoney_py(daily_wage)})",
            deduction_type=DeductionType.absence,
            period_year=year,
            period_month=month,
            auto_generated=True,
        ))

    await db.flush()

    bonuses = (await db.execute(
        select(Bonus).where(
            Bonus.employee_id == data.employee_id,
            Bonus.period_year == year,
            Bonus.period_month == month,
        )
    )).scalars().all()

    deductions = (await db.execute(
        select(Deduction).where(
            Deduction.employee_id == data.employee_id,
            Deduction.period_year == year,
            Deduction.period_month == month,
        )
    )).scalars().all()

    total_bonus = sum(b.amount for b in bonuses)
    total_deduction = sum(d.amount for d in deductions)
    late_deduction = sum(d.amount for d in deductions if d.deduction_type.value == "late")
    leave_deduction = sum(d.amount for d in deductions if d.deduction_type.value == "absence")

    record = SalaryRecord(
        employee_id=data.employee_id,
        period_year=year,
        period_month=month,
        base_salary=emp_base_salary,
        total_bonus=total_bonus,
        total_deduction=total_deduction,
        late_deduction=late_deduction,
        leave_deduction=leave_deduction,
        notes=data.notes,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


def formatMoney_py(amount: Decimal) -> str:
    return f"{int(amount):,} so'm".replace(",", " ")


async def update_salary_status(
    db: AsyncSession, record: SalaryRecord, data: SalaryStatusUpdate
) -> None:
    record.status = data.status
    if data.notes:
        record.notes = data.notes
    if data.status == SalaryStatus.paid:
        record.paid_at = datetime.now(timezone.utc)
    await db.commit()


# ── Daily Earnings ────────────────────────────────────────────

def _calc_hourly_rate(
    base_salary: Decimal,
    hourly_rate: Decimal | None,
    work_hours_per_day: int,
    off_days: list[str],
    year: int,
    month: int,
) -> Decimal:
    if hourly_rate:
        return hourly_rate

    _, days_in_month = monthrange(year, month)
    working_days = sum(
        1 for d in range(1, days_in_month + 1)
        if WEEKDAY_NAMES[date(year, month, d).weekday()] not in off_days
    )
    if working_days == 0:
        working_days = 22

    hours_per_month = working_days * work_hours_per_day
    return base_salary / Decimal(hours_per_month)


async def get_daily_earnings(
    db: AsyncSession,
    employee_id: int,
    year: int,
    month: int,
) -> dict:
    from app.models.attendance import Attendance

    employee = await db.scalar(select(Employee).where(Employee.id == employee_id))
    if not employee:
        raise ValueError("Employee not found")

    emp_base_salary = employee.base_salary
    emp_hourly_rate = employee.hourly_rate
    emp_work_hours = employee.work_hours_per_day or 8
    emp_off_days: list[str] = employee.off_days or []

    hourly_rate = _calc_hourly_rate(
        emp_base_salary, emp_hourly_rate, emp_work_hours, emp_off_days, year, month
    )
    off_days = emp_off_days

    attendances = (await db.execute(
        select(Attendance).where(
            Attendance.employee_id == employee_id,
            func.extract("year", Attendance.date) == year,
            func.extract("month", Attendance.date) == month,
        ).order_by(Attendance.date)
    )).scalars().all()

    att_by_date = {a.date: a for a in attendances}

    _, days_in_month = monthrange(year, month)
    today = date.today()

    days = []
    total_hours = Decimal("0")
    total_earned = Decimal("0")
    today_hours = Decimal("0")
    today_earned = Decimal("0")

    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        if d > today:
            break

        day_name = WEEKDAY_NAMES[d.weekday()]
        is_off = day_name in off_days
        att = att_by_date.get(d)
        worked_hours = Decimal("0")
        earned = Decimal("0")

        if is_off:
            status = "off"
        elif att and att.check_in_time and att.check_out_time:
            ci = datetime.combine(d, att.check_in_time)
            co = datetime.combine(d, att.check_out_time)
            secs = (co - ci).total_seconds()
            if secs > 0:
                worked_hours = Decimal(str(round(secs / 3600, 2)))
                earned = (worked_hours * hourly_rate).quantize(Decimal("1"))
            status = "present"
        elif att and att.check_in_time and not att.check_out_time:
            if d == today:
                ci = datetime.combine(d, att.check_in_time)
                secs = (datetime.now() - ci).total_seconds()
                if secs > 0:
                    worked_hours = Decimal(str(round(secs / 3600, 2)))
                    earned = (worked_hours * hourly_rate).quantize(Decimal("1"))
                status = "active"
            else:
                status = "no_checkout"
        else:
            status = "absent"

        days.append({
            "date": d.isoformat(),
            "day": day_num,
            "weekday": day_name,
            "is_off": is_off,
            "status": status,
            "worked_hours": float(worked_hours),
            "earned": int(earned),
        })

        total_hours += worked_hours
        total_earned += earned
        if d == today:
            today_hours = worked_hours
            today_earned = earned

    return {
        "employee_id": employee_id,
        "year": year,
        "month": month,
        "hourly_rate": int(hourly_rate),
        "base_salary": int(emp_base_salary),
        "today_hours": float(today_hours),
        "today_earned": int(today_earned),
        "total_hours": float(total_hours),
        "total_earned": int(total_earned),
        "days": days,
    }


# ── Bonus ────────────────────────────────────────────────────

async def get_bonuses(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    year: int | None,
    month: int | None,
) -> tuple[int, list[Bonus]]:
    q = select(Bonus)
    if employee_id:
        q = q.where(Bonus.employee_id == employee_id)
    if year:
        q = q.where(Bonus.period_year == year)
    if month:
        q = q.where(Bonus.period_month == month)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def create_bonus(db: AsyncSession, data: BonusCreate, approved_by_id: int) -> Bonus:
    bonus = Bonus(**data.model_dump(), approved_by_id=approved_by_id)
    db.add(bonus)
    await db.commit()
    await db.refresh(bonus)
    return bonus


async def delete_bonus(db: AsyncSession, bonus: Bonus) -> None:
    await db.delete(bonus)
    await db.commit()


# ── Deduction ────────────────────────────────────────────────

async def get_deductions(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    year: int | None,
    month: int | None,
) -> tuple[int, list[Deduction]]:
    q = select(Deduction)
    if employee_id:
        q = q.where(Deduction.employee_id == employee_id)
    if year:
        q = q.where(Deduction.period_year == year)
    if month:
        q = q.where(Deduction.period_month == month)

    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    items = (await db.execute(q.offset((page - 1) * size).limit(size))).scalars().all()
    return total, list(items)


async def create_deduction(db: AsyncSession, data: DeductionCreate) -> Deduction:
    deduction = Deduction(**data.model_dump())
    db.add(deduction)
    await db.commit()
    await db.refresh(deduction)
    return deduction


async def delete_deduction(db: AsyncSession, deduction: Deduction) -> None:
    await db.delete(deduction)
    await db.commit()