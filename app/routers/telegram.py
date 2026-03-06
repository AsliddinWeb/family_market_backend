from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import TZ, settings
from app.core.database import get_db
from app.core.dependencies import get_admin
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import CheckInRequest, CheckOutRequest
from app.services import attendance_service
from app.services.telegram_service import delete_webhook, send_message, set_webhook

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


@router.post("/set-webhook")
async def setup_webhook(_: User = Depends(get_admin)):
    url = f"{settings.BASE_URL}/api/telegram/webhook"
    return await set_webhook(url)


@router.post("/delete-webhook")
async def remove_webhook(_: User = Depends(get_admin)):
    return await delete_webhook()


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    if settings.TELEGRAM_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    body = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()

    employee = await db.scalar(
        select(Employee).where(Employee.telegram_user_id == chat_id)
    )
    if not employee:
        await send_message(chat_id, "❌ Siz tizimda ro'yxatdan o'tmagansiz.")
        return {"ok": True}

    # UTC → UTC+5
    utc_dt = datetime.fromtimestamp(message.get("date", 0), tz=timezone.utc)
    local_dt = utc_dt.astimezone(TZ)
    current_time = local_dt.time()
    today = local_dt.date()

    if text.lower() in ("/checkin", "keldi", "✅"):
        existing = await attendance_service.get_by_employee_date(db, employee.id, today)
        if existing and existing.check_in_time:
            await send_message(
                chat_id,
                f"ℹ️ Siz bugun allaqachon kelgansiz\n🕐 {existing.check_in_time}",
            )
        else:
            try:
                record = await attendance_service.check_in(
                    db, CheckInRequest(employee_id=employee.id, check_in_time=current_time)
                )
                status_text = "⏰ Kech" if record.late_minutes > 0 else "✅ O'z vaqtida"
                msg = f"*Kelish qayd etildi!*\n📅 {today}\n🕐 {record.check_in_time}\n{status_text}"
                if record.late_minutes > 0:
                    msg += f" ({record.late_minutes} daqiqa kech)"
                await send_message(chat_id, msg)
            except Exception as e:
                await send_message(chat_id, f"❌ Xato: {str(e)}")

    elif text.lower() in ("/checkout", "ketdi", "🚪"):
        existing = await attendance_service.get_by_employee_date(db, employee.id, today)
        if not existing or not existing.check_in_time:
            await send_message(chat_id, "❌ Avval kelishni qayd eting — /checkin")
        elif existing.check_out_time:
            await send_message(
                chat_id,
                f"ℹ️ Siz bugun allaqachon ketgansiz\n🕐 {existing.check_out_time}",
            )
        else:
            try:
                record = await attendance_service.check_out(
                    db, CheckOutRequest(employee_id=employee.id, check_out_time=current_time)
                )
                await send_message(
                    chat_id,
                    f"*Ketish qayd etildi!*\n📅 {today}\n🕐 {record.check_out_time}",
                )
            except ValueError as e:
                await send_message(chat_id, f"❌ {str(e)}")

    elif text.lower() in ("/status", "holat"):
        summary = await attendance_service.get_summary(db, employee.id, today.year, today.month)
        await send_message(
            chat_id,
            f"📊 *{today.year}-{today.month:02d} statistika*\n\n"
            f"✅ Keldi: {summary.present}\n"
            f"⏰ Kech: {summary.late}\n"
            f"❌ Kelmadi: {summary.absent}\n"
            f"🕐 Jami kechikish: {summary.total_late_minutes} daqiqa",
        )

    else:
        await send_message(
            chat_id,
            "📋 *Buyruqlar:*\n"
            "✅ /checkin — Kelishni qayd etish\n"
            "🚪 /checkout — Ketishni qayd etish\n"
            "📊 /status — Oylik statistika",
        )

    return {"ok": True}