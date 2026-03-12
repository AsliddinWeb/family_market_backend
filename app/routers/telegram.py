import base64
import hashlib
import hmac
import json
import os
import urllib.parse
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import TZ, settings
from app.core.database import get_db
from app.core.dependencies import get_admin
from app.models.employee import Employee
from app.models.user import User
from app.schemas.attendance import CheckInRequest, CheckOutRequest
from app.services import attendance_service
from app.services.telegram_service import delete_webhook, send_message, set_webhook

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


# ─── WebApp HTML serve ────────────────────────────────────────────────────────

@router.get("/webapp/checkin", response_class=HTMLResponse)
async def webapp_checkin_page():
    with open("webapp/checkin.html", "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("%%API_BASE%%", settings.BASE_URL)
    return HTMLResponse(content=html)


# ─── Webhook setup ────────────────────────────────────────────────────────────

@router.post("/set-webhook")
async def setup_webhook(_: User = Depends(get_admin)):
    url = f"{settings.BASE_URL}/api/telegram/webhook"
    return await set_webhook(url)


@router.post("/delete-webhook")
async def remove_webhook(_: User = Depends(get_admin)):
    return await delete_webhook()


# ─── WebApp auth yordamchi ────────────────────────────────────────────────────

def verify_telegram_webapp_data(init_data: str, bot_token: str) -> dict | None:
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )

        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

        if not hmac.compare_digest(expected_hash, received_hash):
            return None

        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return {}
    except Exception:
        return None


# ─── WebApp Check-in ──────────────────────────────────────────────────────────

class WebAppCheckInRequest(BaseModel):
    init_data: str
    photo_base64: str
    latitude: float
    longitude: float
    face_match_score: float = 0.0


class WebAppCheckInResponse(BaseModel):
    ok: bool
    message: str
    status: str | None = None
    late_minutes: int = 0
    is_holiday: bool = False
    bonus_amount: str | None = None
    distance_meters: float | None = None


@router.post("/webapp-checkin", response_model=WebAppCheckInResponse)
async def webapp_check_in(
    data: WebAppCheckInRequest,
    db: AsyncSession = Depends(get_db),
):
    user_data = verify_telegram_webapp_data(data.init_data, settings.TELEGRAM_BOT_TOKEN)
    if user_data is None:
        raise HTTPException(status_code=403, detail="Telegram ma'lumotlari noto'g'ri")

    telegram_user_id = str(user_data.get("id"))

    employee = await db.scalar(
        select(Employee)
        .options(selectinload(Employee.branch), selectinload(Employee.user))
        .where(Employee.telegram_user_id == telegram_user_id)
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Siz tizimda ro'yxatdan o'tmagansiz")

    if not employee.is_active:
        raise HTTPException(status_code=403, detail="Sizning hisobingiz faol emas")

    FACE_THRESHOLD = 0.6
    if employee.face_photo and data.face_match_score < FACE_THRESHOLD:
        raise HTTPException(
            status_code=422,
            detail=f"Yuz tanishda mos kelmadi (score: {data.face_match_score:.2f}). "
                   f"Ruxsat berilgan minimum: {FACE_THRESHOLD}"
        )

    photo_path: str | None = None
    try:
        media_dir = os.path.join(settings.MEDIA_DIR, "attendance")
        os.makedirs(media_dir, exist_ok=True)

        utc_now = datetime.now(tz=TZ)
        filename = f"{employee.id}_{utc_now.strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = os.path.join(media_dir, filename)

        img_data = base64.b64decode(data.photo_base64)
        with open(file_path, "wb") as f:
            f.write(img_data)

        photo_path = f"attendance/{filename}"
    except Exception:
        pass

    local_dt = datetime.now(tz=TZ)
    check_in_req = CheckInRequest(
        employee_id=employee.id,
        check_in_time=local_dt.time(),
        check_in_photo=photo_path,
        check_in_location={
            "latitude": data.latitude,
            "longitude": data.longitude,
        },
    )

    try:
        record = await attendance_service.check_in(db, check_in_req)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    bonus_amount = None
    if record.status == "holiday":
        hourly = employee.get_effective_hourly_rate()
        from decimal import Decimal
        amount = (hourly * Decimal(employee.work_hours_per_day)).quantize(Decimal("0.01"))
        bonus_amount = f"{amount:,.0f} so'm"

    status_text = {
        "present": "✅ O'z vaqtida",
        "late": f"⏰ Kech keldi (+{record.late_minutes} daqiqa)",
        "holiday": "🎉 Dam olish kuni",
    }.get(record.status, "✅ Qayd etildi")

    msg = (
        f"📍 *Kelish qayd etildi!*\n"
        f"📅 {local_dt.strftime('%d.%m.%Y')}\n"
        f"🕐 {record.check_in_time}\n"
        f"{status_text}"
    )
    if bonus_amount:
        msg += f"\n💰 Bonus: {bonus_amount}"

    await send_message(employee.user.phone if employee.user else telegram_user_id, msg)

    distance = None
    if employee.branch and employee.branch.latitude:
        from app.services.attendance_service import haversine_meters
        distance = haversine_meters(
            float(employee.branch.latitude), float(employee.branch.longitude),
            data.latitude, data.longitude,
        )

    return WebAppCheckInResponse(
        ok=True,
        message="Kelish muvaffaqiyatli qayd etildi",
        status=record.status,
        late_minutes=record.late_minutes,
        is_holiday=(record.status == "holiday"),
        bonus_amount=bonus_amount,
        distance_meters=round(distance, 1) if distance else None,
    )


# ─── Employee info — WebApp uchun ────────────────────────────────────────────

@router.get("/webapp-employee-info")
async def webapp_employee_info(
    init_data: str,
    db: AsyncSession = Depends(get_db),
):
    user_data = verify_telegram_webapp_data(init_data, settings.TELEGRAM_BOT_TOKEN)
    if user_data is None:
        raise HTTPException(status_code=403, detail="Noto'g'ri initData")

    telegram_user_id = str(user_data.get("id"))
    employee = await db.scalar(
        select(Employee)
        .options(selectinload(Employee.branch), selectinload(Employee.user))
        .where(Employee.telegram_user_id == telegram_user_id)
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Xodim topilmadi")

    from datetime import date
    today = datetime.now(tz=TZ).date()
    today_att = await attendance_service.get_by_employee_date(db, employee.id, today)

    return {
        "employee_id":    employee.id,
        "full_name":      employee.user.full_name if employee.user else "",
        "face_photo_url": (
            f"{settings.BASE_URL}/media/{employee.face_photo}"
            if employee.face_photo else None
        ),
        "branch": {
            "name":            employee.branch.name if employee.branch else "",
            "latitude":        float(employee.branch.latitude) if employee.branch and employee.branch.latitude else None,
            "longitude":       float(employee.branch.longitude) if employee.branch and employee.branch.longitude else None,
            "radius_meters":   employee.branch.radius_meters if employee.branch else 200,
            "work_start_time": str(employee.branch.work_start_time) if employee.branch else "09:00:00",
        },
        "today_checked_in":  bool(today_att and today_att.check_in_time),
        "today_checked_out": bool(today_att and today_att.check_out_time),
        "is_off_day":        employee.is_off_day(today),
    }


# ─── Bot webhook ─────────────────────────────────────────────────────────────

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
        select(Employee)
        .options(selectinload(Employee.user))
        .where(Employee.telegram_user_id == chat_id)
    )

    webapp_url = f"{settings.BASE_URL}/api/telegram/webapp/checkin"

    if text.startswith("/start"):
        if not employee:
            await send_message(chat_id, "❌ Siz tizimda ro'yxatdan o'tmagansiz. HR bo'limiga murojaat qiling.")
            return {"ok": True}

        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "📍 *Davomat belgilash*\nQuyidagi tugmani bosib kelishingizni qayd eting:",
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [[{
                            "text": "✅ Davomat belgilash",
                            "web_app": {"url": webapp_url},
                        }]]
                    },
                },
                timeout=10,
            )
        return {"ok": True}

    if not employee:
        await send_message(chat_id, "❌ Siz tizimda ro'yxatdan o'tmagansiz.")
        return {"ok": True}

    utc_dt = datetime.fromtimestamp(message.get("date", 0), tz=timezone.utc)
    local_dt = utc_dt.astimezone(TZ)
    today = local_dt.date()

    if text.lower() in ("/status", "holat"):
        summary = await attendance_service.get_summary(db, employee.id, today.year, today.month)
        await send_message(
            chat_id,
            f"📊 *{today.year}-{today.month:02d} statistika*\n\n"
            f"✅ Keldi: {summary.present}\n"
            f"⏰ Kech: {summary.late}\n"
            f"❌ Kelmadi: {summary.absent}\n"
            f"🎉 Dam olish: {summary.holiday}\n"
            f"🕐 Jami kechikish: {summary.total_late_minutes} daqiqa",
        )
    else:
        import httpx
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": "📋 *Buyruqlar:*\n📊 /status — Oylik statistika\n\nDavomat belgilash uchun:",
                    "parse_mode": "Markdown",
                    "reply_markup": {
                        "inline_keyboard": [[{
                            "text": "✅ Davomat belgilash",
                            "web_app": {"url": webapp_url},
                        }]]
                    },
                },
                timeout=10,
            )

    return {"ok": True}