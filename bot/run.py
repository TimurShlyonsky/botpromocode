import datetime
from bot.parser import fetch_archive_news, extract_promo_from_news
from bot.storage import load_codes, save_codes
from telegram import Bot
import os


BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send(code, title, url):
    bot = Bot(BOT_TOKEN)
    bot.send_message(
        CHAT_ID,
        (
            f"✨ Новый промокод: <b>{code}</b>\n"
            f"📰 <a href=\"{url}\">{title}</a>"
        ),
        parse_mode="HTML",
        disable_web_page_preview=False,
    )


def run():
    today = datetime.date.today()
    year, month = today.year, today.month

    print(f"🚀 Checking promos for {year}-{month:02d}")

    stored = load_codes()
    stored_codes = {x["code"] for x in stored}

    urls = fetch_archive_news(year, month)
    if not urls:
        print("⚠️ No URLs this month")
        return

    new_items = []

    for url in urls:
        items = extract_promo_from_news(url)
        for item in items:
            if item["code"] not in stored_codes:
                stored.append(item)
                new_items.append(item)
                stored_codes.add(item["code"])
                print(f"✨ NEW: {item['code']} — {url}")

    if new_items:
        save_codes(stored)
        for n in new_items:
            send(n["code"], n["title"], n["url"])
        print(f"💾 Saved {len(new_items)} codes")
    else:
        print("ℹ️ No new promo codes")


if __name__ == "__main__":
    run()
