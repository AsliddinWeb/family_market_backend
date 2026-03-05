from datetime import date, time as time_type

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_admin
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import CheckInRequest, CheckOutRequest
from app.services import attendance_service
from app.services.telegram_service import set_webhook, delete_webhook

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


# ── Webhook setup ────────────────────────────────────────────

@router.post("/set-webhook")
async def setup_webhook(
    _: User = Depends(get_admin),
):
    url = f"{settings.BASE_URL}/api/telegram/webhook"
    result = await set_webhook(url)
    return result


@router.post("/delete-webhook")
async def remove_webhook(
    _: User = Depends(get_admin),
):
    return await delete_webhook()


# ── Webhook handler ──────────────────────────────────────────

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(None),
):
    # Secret token tekshirish
    if settings.TELEGRAM_SECRET:
        if x_telegram_bot_api_secret_token != settings.TELEGRAM_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    body = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return {"ok": True}

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()

    # Telegram user_id orqali xodimni topish
    employee = await db.scalar(
        select(Employee).where(Employee.telegram_user_id == chat_id)
    )

    if not employee:
        from app.services.telegram_service import send_message
        await send_message(chat_id, "❌ Siz tizimda ro'yxatdan o'tmagansiz.")
        return {"ok": True}

    now = date.today()
    current_time = time_type(
        int(message.get("date", 0)) % 86400 // 3600,
        (int(message.get("date", 0)) % 3600) // 60,
    )

    from app.services.telegram_service import send_message

    if text.lower() in ("/checkin", "keldi", "✅"):
        try:
            record = await attendance_service.check_in(
                db,
                CheckInRequest(
                    employee_id=employee.id,
                    check_in_time=current_time,
                ),
            )
            status_text = "⏰ Kech" if record.late_minutes > 0 else "✅ O'z vaqtida"
            msg = (
                f"*Kelish qayd etildi!*\n"
                f"📅 {now}\n"
                f"🕐 {record.check_in_time}\n"
                f"{status_text}"
            )
            if record.late_minutes > 0:
                msg += f" ({record.late_minutes} daqiqa kech)"
            await send_message(chat_id, msg)
        except Exception as e:
            await send_message(chat_id, f"❌ Xato: {str(e)}")

    elif text.lower() in ("/checkout", "ketdi", "🚪"):
        try:
            record = await attendance_service.check_out(
                db,
                CheckOutRequest(
                    employee_id=employee.id,
                    check_out_time=current_time,
                ),
            )
            await send_message(
                chat_id,
                f"*Ketish qayd etildi!*\n📅 {now}\n🕐 {record.check_out_time}",
            )
        except ValueError as e:
            await send_message(chat_id, f"❌ {str(e)}")

    elif text.lower() in ("/status", "holat"):
        summary = await attendance_service.get_summary(
            db, employee.id, now.year, now.month
        )
        await send_message(
            chat_id,
            f"📊 *{now.year}-{now.month:02d} statistika*\n\n"
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