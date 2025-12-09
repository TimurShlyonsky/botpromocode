import re
import requests
import json
import logging
import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "YOUR_TOKEN_HERE"  # ⚠️ ВСТАВИ СВОЙ ТОКЕН

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

ARCHIVE_URL = "https://www.lotro.com/archive/2025/12"
SENT_CODES_FILE = "sent_codes.json"
BLACKLIST = {"UPDATE", "REMINDER", "THROUGH"}


def load_sent_codes():
    try:
        with open(SENT_CODES_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()


def save_sent_codes(codes):
    with open(SENT_CODES_FILE, "w") as f:
        json.dump(list(codes), f)


def fetch_articles_from_archive():
    logger.info("📚 Загружаю архив...")
    resp = requests.get(ARCHIVE_URL, headers=HEADERS)
    if resp.status_code != 200:
        logger.warning("Не удалось загрузить архив")
        return []

    match = re.search(r"window\.SSG\.archive\.articles\s*=\s*(\[.*?\]);",
                      resp.text, re.S)
    if not match:
        logger.error("❌ JSON со статьями не найден в архиве!")
        return []

    articles = json.loads(match.group(1))
    urls = [
        f"https://www.lotro.com/news/{a['pageName']}"
        for a in articles if "pageName" in a
    ]
    logger.info(f"📝 Статей найдено: {len(urls)}")
    return urls


def extract_codes(html: str):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True).upper()
    found = re.findall(r"COUPON CODE[:\s]+([A-Z0-9]+)", text)
    found = {
        c for c in found
        if len(c) >= 6 and c not in BLACKLIST
    }
    return sorted(found)


async def check_lotro_impl(context_or_chat):
    logger.info("🔍 Проверяю промокоды LOTRO...")

    urls = fetch_articles_from_archive()
    if not urls:
        await context_or_chat.bot.send_message(
            chat_id=context_or_chat.effective_chat.id
            if hasattr(context_or_chat, "effective_chat")
            else context_or_chat.job.data,
            text="❌ Не удалось получить список статей"
        )
        return

    sent_codes = load_sent_codes()
    new_codes = []

    for url in urls[:10]:  # проверяем свежие
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            logger.warning(f"⚠️ Пропускаю {url}")
            continue

        codes = extract_codes(resp.text)
        if codes:
            logger.info(f"🧩 {url}: {codes}")
            for code in codes:
                if code not in sent_codes:
                    new_codes.append((code, url))
                    sent_codes.add(code)

    save_sent_codes(sent_codes)

    chat_id = (
        context_or_chat.effective_chat.id
        if hasattr(context_or_chat, "effective_chat")
        else context_or_chat.job.data
    )

    if new_codes:
        text = "🔥 Новые промокоды:\n" + "\n".join(
            f"✔ <b>{c}</b> — {u}" for c, u in new_codes
        )
    else:
        text = "ℹ️ Новых промокодов нет."

    await context_or_chat.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")


async def cmd_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await check_lotro_impl(update)


def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Команда вручную
    application.add_handler(CommandHandler("check_lotro", cmd_check))

    # Автопроверка – пятница 12:00 (Калининград GMT+2)
    kaliningrad = ZoneInfo("Europe/Kaliningrad")
    job_queue = application.job_queue
    job_queue.run_daily(
        check_lotro_impl,
        time=datetime.time(hour=12, minute=0, tzinfo=kaliningrad),
        days=(4,),  # 0=Пн...4=Пт
        data=YOUR_CHAT_ID_HERE  # ⚠️ ВСТАВИ ТВОЙ CHAT_ID
    )

    logger.info("🤖 Бот запущен, жду команды...")
    application.run_polling()


if __name__ == "__main__":
    main()
