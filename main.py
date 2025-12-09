import os
import re
import json
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from telegram.constants import ParseMode

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # GitHub Secret
TARGET_CHAT_ID = -1003385030396    # Твой канал
TIMEZONE = "Europe/London"         # Автозапуск в пятницу 12:00

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

BLACKLIST = {"UPDATE", "REMINDER", "THROUGH"}
SENT_FILE = "sent_codes.json"

# =================================================
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)


def load_sent_codes():
    try:
        with open(SENT_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()


def save_sent_codes(data):
    with open(SENT_FILE, "w") as f:
        json.dump(list(data), f)


# ================= Получение ссылок на статьи =================
def fetch_articles_from_archive():
    now = datetime.utcnow()
    year = now.year
    month = now.month

    url = f"https://www.lotro.com/archive/{year}/{month:02d}"
    logging.info(f"Запрашиваю архив: {url}")
    resp = requests.get(url, headers=HEADERS)

    if resp.status_code != 200:
        logging.error(f"Ошибка загрузки архива ({resp.status_code})")
        return []

    match = re.search(
        r"window\.SSG\.archive\.articles\s*=\s*(\[.*?\]);",
        resp.text,
        re.S
    )
    if not match:
        logging.warning("JSON window.SSG.archive.articles не найден")
        return []

    articles = json.loads(match.group(1))

    urls = [
        f"https://www.lotro.com/news/{a['pageName']}"
        for a in articles if "pageName" in a
    ]

    logging.info(f"📄 Найдено статей в архиве: {len(urls)}")

    return urls


# ================= Поиск промокодов в тексте =================
def extract_coupon_codes(html):
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True).upper()

    codes = set()

    # Основной вариант
    matches = re.findall(r"COUPON CODE[:\s]+([A-Z0-9]+)", text)
    codes.update(matches)

    # Фильтрация мусора
    codes = {
        c for c in codes
        if len(c) >= 6 and c not in BLACKLIST
    }

    return sorted(codes)


# ================= Основная функция проверки =================
def check_lotro_news():
    logging.info("🔍 Старт проверки LOTRO промокодов...")

    urls = fetch_articles_from_archive()
    if not urls:
        return [], "❌ Не удалось получить список новостей"

    sent = load_sent_codes()
    new_found = []

    for url in urls:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code != 200:
            continue

        codes = extract_coupon_codes(resp.text)
        if not codes:
            logging.info(f"… нет промокодов → {url}")
            continue

        logging.info(f"🧩 Найдено в {url}: {codes}")

        for code in codes:
            if code not in sent:
                sent.add(code)
                new_found.append((code, url))
                logging.info(f"🔥 Новый промокод: {code}")

    save_sent_codes(sent)

    return new_found, None


# ================= Handlers =================
async def cmd_check(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🕵️ Проверяю новости LOTRO на промокоды..."
    )

    new_codes, err = check_lotro_news()

    if err:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=err)
        return

    if not new_codes:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="ℹ️ Новых промокодов LOTRO не найдено."
        )
        return

    for code, url in new_codes:
        msg = f"🎁 Новый промокод LOTRO!\nКод: <b>{code}</b>\n{url}"
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=msg,
            parse_mode=ParseMode.HTML
        )


# ================= Автозапуск по расписанию =================
async def auto_check(context: CallbackContext):
    new_codes, _ = check_lotro_news()

    if not new_codes:
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text="ℹ️ Новых промокодов LOTRO сегодня нет."
        )
        return

    for code, url in new_codes:
        msg = f"🎁 Новый промокод LOTRO!\nКод: <b>{code}</b>\n{url}"
        await context.bot.send_message(
            chat_id=TARGET_CHAT_ID,
            text=msg,
            parse_mode=ParseMode.HTML
        )


# ================= Старт бота =================
def main():
    if not BOT_TOKEN:
        logging.error("❌ Нет BOT_TOKEN в GitHub Secrets!")
        return

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Команда вручную
    application.add_handler(CommandHandler("check_lotro", cmd_check))

    # Автопроверка каждую пятницу в 12:00 (Europe/London)
    job_queue = application.job_queue
    job_queue.run_daily(
        auto_check,
        time=datetime.time(hour=12, minute=0),
        days=(4,),  # Friday
        name="lotro_auto_check",
        timezone=TIMEZONE,
    )

    logging.info("🤖 Бот запущен!")
    logging.info("⏰ Автопроверка: Пятница 12:00 (Europe/London)")
    logging.info("💬 Команда ручной проверки: /check_lotro")

    application.run_polling()


if __name__ == "__main__":
    main()
