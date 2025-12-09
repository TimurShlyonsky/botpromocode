import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_promo(code: str, description: str | None, url: str):
    """Отправляем сообщение в Telegram канал."""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️ BOT_TOKEN or TELEGRAM_CHAT_ID is not set!")
        return

    text_lines = [
        "🎁 *Новый промокод LOTRO!*",
        f"*Код:* `{code}`"
    ]

    if description:
        text_lines.append(f"_Что даёт_:* {description}")

    text_lines.append(url)

    message = "\n".join(text_lines)

    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
    )

