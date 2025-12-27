import os
import json
import re
from pathlib import Path
from telethon import TelegramClient

# ====== ENV ======
API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
CHANNEL = os.getenv("TG_CHANNEL")  # без @

# ====== FILES ======
TELEGRAM_STATE_PATH = Path("data/promo_codes_telegram.json")

# ====== REGEX ======
PROMO_CODE_PATTERN = re.compile(r"\b[A-Z]{6,20}\b")


def extract_promo_codes(text: str) -> list[str]:
    """
    Извлекает промокоды из текста сообщения.
    """
    if not text:
        return []

    return PROMO_CODE_PATTERN.findall(text)


def load_telegram_state() -> int:
    """
    Загружает last_message_id из JSON.
    Если файла нет или формат некорректный — возвращает 0.
    """
    if not TELEGRAM_STATE_PATH.exists():
        return 0

    try:
        data = json.loads(TELEGRAM_STATE_PATH.read_text(encoding="utf-8"))
        return int(data.get("last_message_id", 0))
    except Exception:
        return 0


def save_telegram_state(last_message_id: int) -> None:
    """
    Сохраняет last_message_id в JSON.
    """
    TELEGRAM_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    TELEGRAM_STATE_PATH.write_text(
        json.dumps(
            {
                "last_message_id": last_message_id
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


async def get_promo_items_from_telegram() -> list[dict]:
    """
    Читает ТОЛЬКО новые сообщения Telegram-канала
    (начиная с last_message_id) и возвращает список:

    [
      { "code": "...", "url": "https://t.me/<channel>/<message_id>" }
    ]
    """
    new_items: list[dict] = []
    last_message_id = load_telegram_state()
    max_message_id = last_message_id

    async with TelegramClient("promo_session", API_ID, API_HASH) as client:
        channel = await client.get_entity(CHANNEL)

        async for message in client.iter_messages(channel, min_id=last_message_id):
            if not message.text:
                continue

            codes = extract_promo_codes(message.text)
            if not codes:
                continue

            post_url = f"https://t.me/{CHANNEL}/{message.id}"

            for code in codes:
                new_items.append({
                    "code": code,
                    "url": post_url,
                })

            # обновляем максимальный message.id
            if message.id > max_message_id:
                max_message_id = message.id

    # сохраняем новое состояние только если были новые сообщения
    if max_message_id > last_message_id:
        save_telegram_state(max_message_id)

    return new_items
