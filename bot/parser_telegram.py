import os
import json
import re
from pathlib import Path
from telethon import TelegramClient

STATE_PATH = Path("data/telegram_state.json")

PROMO_CODE_PATTERN = re.compile(r"\b[A-Z]{6,20}\b")

# Строгие паттерны для дропсов
DROP_PATTERNS = [
    re.compile(r"\btwitch\s+drops\b", re.IGNORECASE),
    re.compile(r"\bвнутриигровые\s+награды\b", re.IGNORECASE),
]


# --------------------
# Telegram ENV
# --------------------
def get_telegram_env():
    api_id = os.getenv("TG_API_ID")
    api_hash = os.getenv("TG_API_HASH")
    channel = os.getenv("TG_CHANNEL")

    if not api_id or not api_hash or not channel:
        raise RuntimeError("Telegram env vars are not set")

    return int(api_id), api_hash, channel


# --------------------
# Promo codes
# --------------------
def extract_promo_codes(text: str) -> list[str]:
    if not text:
        return []
    return PROMO_CODE_PATTERN.findall(text)


# --------------------
# Drops detection (STRICT)
# --------------------
def is_drop_announcement(text: str) -> bool:
    if not text:
        return False

    return any(pattern.search(text) for pattern in DROP_PATTERNS)


# --------------------
# Telegram state
# --------------------
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


# --------------------
# Main parser
# --------------------
async def get_promo_items_from_telegram() -> dict:
    """
    Возвращает:
    {
        "promos": [{ "code": "...", "url": "..." }],
        "drops":  [{ "url": "...", "message_id": int }]
    }
    """
    api_id, api_hash, channel_name = get_telegram_env()

    last_message_id = load_last_message_id()
    max_message_id = last_message_id

    promo_items: list[dict] = []
    drop_items: list[dict] = []

    async with TelegramClient("promo_session", api_id, api_hash) as client:
        channel = await client.get_entity(channel_name)

        async for message in client.iter_messages(channel, min_id=last_message_id):
            if not message.text:
                continue

            text = message.text
            post_url = f"https://t.me/{channel_name}/{message.id}"

            # 🎁 Промокоды
            for code in extract_promo_codes(text):
                promo_items.append({
                    "code": code,
                    "url": post_url,
                })

            # 🎮 Twitch Drops / внутриигровые награды
            if is_drop_announcement(text):
                drop_items.append({
                    "url": post_url,
                    "message_id": message.id,
                })

            if message.id > max_message_id:
                max_message_id = message.id

    # обновляем курсор Telegram
    if max_message_id > last_message_id:
        save_last_message_id(max_message_id)

    return {
        "promos": promo_items,
        "drops": drop_items,
    }
