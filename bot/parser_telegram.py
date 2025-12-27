import os
import json
import re
from pathlib import Path
from telethon import TelegramClient

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
CHANNEL = os.getenv("TG_CHANNEL")

STATE_PATH = Path("data/telegram_state.json")

PROMO_CODE_PATTERN = re.compile(r"\b[A-Z]{6,20}\b")


def extract_promo_codes(text: str) -> list[str]:
    if not text:
        return []
    return PROMO_CODE_PATTERN.findall(text)


def load_last_message_id() -> int:
    if not STATE_PATH.exists():
        return 0

    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return int(data.get("last_message_id", 0))
    except Exception:
        return 0


def save_last_message_id(message_id: int) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps({"last_message_id": message_id}, indent=2),
        encoding="utf-8",
    )


async def get_promo_items_from_telegram() -> list[dict]:
    last_message_id = load_last_message_id()
    max_message_id = last_message_id
    items: list[dict] = []

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
                items.append({
                    "code": code,
                    "url": post_url,
                })

            if message.id > max_message_id:
                max_message_id = message.id

    if max_message_id > last_message_id:
        save_last_message_id(max_message_id)

    return items
