import os
import json
import re
from pathlib import Path
from telethon import TelegramClient

STATE_PATH = Path("data/telegram_state.json")
DROPS_STATE_PATH = Path("data/telegram_drops_state.json")

PROMO_CODE_PATTERN = re.compile(r"\b[A-Z]{6,20}\b")

DROP_KEYWORDS = [
    "twitch drops",
    "внутриигровые награды",
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
# Drops detection
# --------------------
def is_drop_announcement(text: str) -> bool:
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in DROP_KEYWORDS)


def load_last_drop_message_id() -> int:
    if not DROPS_STATE_PATH.exists():
        return 0
    try:
        data = json.loads(DROPS_STATE_PATH.read_text(encoding="utf-8"))
        return int(data.get("last_drop_message_id", 0))
    except Exception:
        return 0


def save_last_drop_message_id(message_id: int) -> None:
    DROPS_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DROPS_STATE_PATH.write_text(
        json.dumps({"last_drop_message_id": message_id}, indent=2),
        encoding="utf-8",
    )


# --------------------
# General telegram state
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
        "drops":  [{ "url": "..." }]
    }
    """
    api_id, api_hash, channel_name = get_telegram_env()

    last_message_id = load_last_message_id()
    last_drop_message_id = load_last_drop_message_id()

    max_message_id = last_message_id
    max_drop_message_id = last_drop_message_id

    promo_items = []
    drop_items = []

    async with TelegramClient("promo_session", api_id, api_hash) as client:
        channel = await client.get_entity(channel_name)

        async for message in client.iter_messages(channel, min_id=last_message_id):
            if not message.text:
                continue

            text = message.text
            post_url = f"https://t.me/{channel_name}/{message.id}"

            # 🎁 Промокоды
            codes = extract_promo_codes(text)
            for code in codes:
                promo_items.append({
                    "code": code,
                    "url": post_url,
                })

            # 🎮 Twitch Drops / внутриигровые награды (ТОЛЬКО НОВЫЕ)
            if is_drop_announcement(text) and message.id > last_drop_message_id:
                drop_items.append({
                    "url": post_url,
                    "message_id": message.id,
                })
                if message.id > max_drop_message_id:
                    max_drop_message_id = message.id

            if message.id > max_message_id:
                max_message_id = message.id

    # сохраняем общий telegram state
    if max_message_id > last_message_id:
        save_last_message_id(max_message_id)

    # сохраняем state дропсов
    if max_drop_message_id > last_drop_message_id:
        save_last_drop_message_id(max_drop_message_id)

    return {
        "promos": promo_items,
        "drops": drop_items,
    }
