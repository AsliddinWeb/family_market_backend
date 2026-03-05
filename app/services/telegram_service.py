import httpx

from app.core.config import settings

TELEGRAM_API = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_message(
    chat_id: str | int,
    text: str,
    parse_mode: str = "Markdown",
) -> dict:
    """Telegram foydalanuvchiga xabar yuborish."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            },
            timeout=10,
        )
        return resp.json()


async def send_photo(
    chat_id: str | int,
    photo_url: str,
    caption: str = "",
) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/sendPhoto",
            json={
                "chat_id": chat_id,
                "photo": photo_url,
                "caption": caption,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        return resp.json()


async def set_webhook(webhook_url: str) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{TELEGRAM_API}/setWebhook",
            json={"url": webhook_url, "secret_token": settings.TELEGRAM_SECRET},
            timeout=10,
        )
        return resp.json()


async def delete_webhook() -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{TELEGRAM_API}/deleteWebhook", timeout=10)
        return resp.json()