import asyncio
from datetime import date

from app.tasks.celery_app import celery_app


def run_async(coro):
    """Celery sync context ichida async funksiya ishlatish uchun."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.attendance_tasks.mark_absent_employees")
def mark_absent_employees():
    """
    Har kuni kechqurun — bugun hech qanday attendance yozuvi
    bo'lmagan aktiv xodimlarni 'absent' deb belgilaydi.
    """
    return run_async(_mark_absent_employees_async())


async def _mark_absent_employees_async():
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.attendance import Attendance, AttendanceStatus, AttendanceSource
    from app.models.employee import Employee

    today = date.today()

    async with AsyncSessionLocal() as db:
        # Bugun attendance yozuvi bor xodimlar
        marked_ids = (await db.execute(
            select(Attendance.employee_id).where(Attendance.date == today)
        )).scalars().all()

        # Aktiv xodimlar — yozuv yo'qlar
        employees = (await db.execute(
            select(Employee).where(
                Employee.is_active == True,
                Employee.is_deleted == False,
                Employee.id.not_in(marked_ids) if marked_ids else True,
            )
        )).scalars().all()

        count = 0
        for emp in employees:
            record = Attendance(
                employee_id=emp.id,
                date=today,
                status=AttendanceStatus.absent,
                source=AttendanceSource.manual,
                late_minutes=0,
            )
            db.add(record)
            count += 1

        await db.commit()
        return {"marked_absent": count, "date": str(today)}