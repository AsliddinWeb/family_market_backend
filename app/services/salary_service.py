from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.salary import Bonus, Deduction, SalaryRecord, SalaryStatus
from app.schemas.salary import (
    BonusCreate,
    DeductionCreate,
    SalaryRecordCreate,
    SalaryStatusUpdate,
)


# ── SalaryRecord ─────────────────────────────────────────────

async def get_salary_records(
    db: AsyncSession,
    page: int,
    size: int,
    employee_id: int | None,
    year: int | None,
    month: int | None,
    status: SalaryStatus | None,
) -> tuple[int, list[SalaryRecord]]:
    q = select(SalaryRecord)

    if employee_id:
        q = q.where(SalaryRecord.employee_id == employee_id)
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
    return await db.scalar(select(SalaryRecord).where(SalaryRecord.id == record_id))


async def create_salary_record(
    db: AsyncSession, data: SalaryRecordCreate, created_by_id: int
) -> SalaryRecord:
    """
    Xodimning base_salary va shu oyga tegishli
    bonus/deduction larni yig'ib SalaryRecord yaratadi.
    """
    from app.models.employee import Employee

    employee = await db.get(Employee, data.employee_id)
    if not employee:
        raise ValueError("Employee not found")

    # Duplicate tekshiruv
    existing = await db.scalar(
        select(SalaryRecord).where(
            SalaryRecord.employee_id == data.employee_id,
            SalaryRecord.period_year == data.period_year,
            SalaryRecord.period_month == data.period_month,
        )
    )
    if existing:
        raise ValueError(f"Salary record already exists for this period")

    # Shu oyning bonus va deductionlarini yig'ish
    bonuses = (await db.execute(
        select(Bonus).where(
            Bonus.employee_id == data.employee_id,
            Bonus.period_year == data.period_year,
            Bonus.period_month == data.period_month,
        )
    )).scalars().all()

    deductions = (await db.execute(
        select(Deduction).where(
            Deduction.employee_id == data.employee_id,
            Deduction.period_year == data.period_year,
            Deduction.period_month == data.period_month,
        )
    )).scalars().all()

    total_bonus = sum(b.amount for b in bonuses)
    total_deduction = sum(d.amount for d in deductions)
    late_deduction = sum(
        d.amount for d in deductions if d.deduction_type.value == "late"
    )
    leave_deduction = sum(
        d.amount for d in deductions if d.deduction_type.value == "absence"
    )

    record = SalaryRecord(
        employee_id=data.employee_id,
        period_year=data.period_year,
        period_month=data.period_month,
        base_salary=employee.base_salary,
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


async def update_salary_status(
    db: AsyncSession, record: SalaryRecord, data: SalaryStatusUpdate
) -> SalaryRecord:
    record.status = data.status
    if data.notes:
        record.notes = data.notes
    if data.status == SalaryStatus.paid:
        record.paid_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(record)
    return record


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


async def create_bonus(
    db: AsyncSession, data: BonusCreate, approved_by_id: int
) -> Bonus:
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