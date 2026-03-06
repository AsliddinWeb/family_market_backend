import asyncio
from datetime import datetime

from app.core.config import TZ
from app.tasks.celery_app import celery_app


def run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.salary_tasks.generate_monthly_salaries")
def generate_monthly_salaries():
    """
    Har oyning 28-sanasida — barcha aktiv xodimlar uchun
    draft holda SalaryRecord yaratadi (agar mavjud bo'lmasa).
    """
    return run_async(_generate_monthly_salaries_async())


async def _generate_monthly_salaries_async():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.employee import Employee
    from app.models.salary import Bonus, Deduction, SalaryRecord, SalaryStatus

    now = datetime.now(tz=TZ)
    year = now.year
    month = now.month

    async with AsyncSessionLocal() as db:
        employees = (await db.execute(
            select(Employee).where(
                Employee.is_active == True,
                Employee.is_deleted == False,
            )
        )).scalars().all()

        created = 0
        skipped = 0

        for emp in employees:
            existing = await db.scalar(
                select(SalaryRecord).where(
                    SalaryRecord.employee_id == emp.id,
                    SalaryRecord.period_year == year,
                    SalaryRecord.period_month == month,
                )
            )
            if existing:
                skipped += 1
                continue

            bonuses = (await db.execute(
                select(Bonus).where(
                    Bonus.employee_id == emp.id,
                    Bonus.period_year == year,
                    Bonus.period_month == month,
                )
            )).scalars().all()

            deductions = (await db.execute(
                select(Deduction).where(
                    Deduction.employee_id == emp.id,
                    Deduction.period_year == year,
                    Deduction.period_month == month,
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
                employee_id=emp.id,
                period_year=year,
                period_month=month,
                base_salary=emp.base_salary,
                total_bonus=total_bonus,
                total_deduction=total_deduction,
                late_deduction=late_deduction,
                leave_deduction=leave_deduction,
                status=SalaryStatus.draft,
            )
            db.add(record)
            created += 1

        await db.commit()
        return {"created": created, "skipped": skipped, "period": f"{year}-{month:02d}"}


@celery_app.task(name="app.tasks.salary_tasks.send_salary_notifications")
def send_salary_notifications(salary_record_id: int):
    """Maosh to'langanda xodimga Telegram xabar yuborish."""
    return run_async(_send_salary_notification_async(salary_record_id))


async def _send_salary_notification_async(salary_record_id: int):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.core.database import AsyncSessionLocal
    from app.models.salary import SalaryRecord
    from app.services.telegram_service import send_message

    async with AsyncSessionLocal() as db:
        record = await db.scalar(
            select(SalaryRecord)
            .options(selectinload(SalaryRecord.employee))
            .where(SalaryRecord.id == salary_record_id)
        )
        if not record or not record.employee:
            return {"error": "record not found"}

        emp = record.employee
        if not emp.telegram_user_id:
            return {"error": "no telegram_user_id"}

        net = record.base_salary + record.total_bonus - record.total_deduction
        text = (
            f"💰 *Maosh to'landi!*\n\n"
            f"📅 Davr: {record.period_year}-{record.period_month:02d}\n"
            f"💵 Asosiy: {record.base_salary:,.0f} so'm\n"
            f"➕ Bonus: {record.total_bonus:,.0f} so'm\n"
            f"➖ Chegirma: {record.total_deduction:,.0f} so'm\n"
            f"✅ Jami: *{net:,.0f} so'm*"
        )
        await send_message(emp.telegram_user_id, text)
        return {"sent": True, "employee_id": emp.id}