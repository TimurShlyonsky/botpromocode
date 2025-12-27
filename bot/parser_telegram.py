import os
import asyncio
import re
from telethon import TelegramClient

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
CHANNEL = os.getenv("TG_CHANNEL")  # без @

PROMO_CODE_PATTERN = re.compile(r"\b[A-Z]{6,20}\b")


def extract_promo_codes(text: str) -> list[str]:
    """
    Извлекает промокоды из текста сообщения.
    """
    if not text:
        return []

    return PROMO_CODE_PATTERN.findall(text)


async def get_promo_items_from_telegram(limit: int = 500) -> list[dict]:
    """
    Читает сообщения из Telegram-канала и возвращает список промокодов
    в формате:
    [
      { "code": "...", "url": "https://t.me/..." }
    ]
    """
    items: dict[str, dict] = {}

    async with TelegramClient("promo_session", API_ID, API_HASH) as client:
        channel = await client.get_entity(CHANNEL)

        async for message in client.iter_messages(channel, limit=limit):
            if not message.text:
                continue

            codes = extract_promo_codes(message.text)
            if not codes:
                continue

            post_url = f"https://t.me/{CHANNEL}/{message.id}"

            for code in codes:
                # если код уже найден ранее — не перезаписываем
                if code not in items:
                    items[code] = {
                        "code": code,
                        "url": post_url,
                    }

    return list(items.values())
