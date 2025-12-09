import os
import requests

TOKEN = os.getenv("BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

API_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


def send_message(text: str):
    if not TOKEN or not CHAT:
        print("🤖 Telegram not configured — skip sending")
        return

    payload = {
        "chat_id": CHAT,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        requests.post(API_URL, json=payload, timeout=10)
    except Exception as e:
        print("❌ Telegram send failed:", e)
