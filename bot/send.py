import os
from telegram import Bot

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=BOT_TOKEN)


def send(code: str, title: str, url: str):
    """Отправляет красивое сообщение в Telegram"""

    if not CHAT_ID:
        print("⚠️ CHAT_ID not set, skipping send()")
        return

    text = (
        f"✨ Новый промокод: <b>{code}</b>\n\n"
        f"<a href=\"{url}\">{title}</a>"
    )

    try:
        bot.send_message(
            chat_id=CHAT_ID,
            text=text,
            parse_mode="HTML",
            disable_web_page_preview=False,  # ✓ для красивой карточки ссылки
        )
        print(f"📨 Sent to Telegram: {code}")
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
