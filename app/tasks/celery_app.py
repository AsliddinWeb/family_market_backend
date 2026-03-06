from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "familymarket",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.attendance_tasks",
        "app.tasks.salary_tasks",
    ],
)

celery_app.conf.timezone = "Asia/Tashkent"
celery_app.conf.enable_utc = True

# Periodic tasks
celery_app.conf.beat_schedule = {
    # Har kuni 23:59 da — davomatsizlarni belgilash
    "mark-absent-daily": {
        "task": "app.tasks.attendance_tasks.mark_absent_employees",
        "schedule": crontab(hour=23, minute=59),
    },
    # Har oyning oxirgi kunida — oylik maoshlarni draft holda yaratish
    "generate-monthly-salaries": {
        "task": "app.tasks.salary_tasks.generate_monthly_salaries",
        "schedule": crontab(hour=22, minute=0, day_of_month="28"),
    },
}

celery_app.conf.broker_connection_retry_on_startup = True