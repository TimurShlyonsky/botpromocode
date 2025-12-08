import os
import re
import json
import logging
import requests
from datetime import datetime
from telegram import Bot
from telegram.ext import (
    Application, CommandHandler
)
from telegram.constants import ParseMode
from bs4 import BeautifulSoup

# ---------------- CONFIG ---------------- #

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
TARGET_CHAT_ID = "-1003385030396"

LOTRO_TEST_NEWS = "https://www.lotro.com/news/lotro-sales-120425-en"

# Слова, которые считаем мусором
BLACKLIST = {"UPDATE", "REMINDER", "ONLINE", "DOC", "DOCTYPE"}

# Файл для запоминания уже отправленных кодов
SENT_CODES_FILE = "sent_codes.json"


# ---------------------------------------- #
#               ЛОГГЕР
# ---------------------------------------- #
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------- #
#           Утилитарные функции
# ---------------------------------------- #
def load_sent_codes():
    if os.path.exists(SENT_CODES_FILE):
        try:
            with open(SENT_CODES_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_sent_codes(codes):
    with open(SENT_CODES_FILE, "w", encoding="utf-8") as f:
        json.dump(list(codes), f, ensure_ascii=False)


def find_codes(text):
    """Ищем слова длиной >= 6, заглавные, без цифр в начале"""
    candidates = re.findall(r"\b[A-Z0-9]{6,}\b", text)
    result = []
    for c in candidates:
        if c.upper() != c:
            continue
        if c in BLACKLIST:
            continue
        # отсекаем если состоит только из цифр
        if c.isdigit():
            continue
        result.append(c)
    return result


def analyze_article(url):
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)
        codes = find_codes(text)
        logger.info(f"🧩 Найдено в {url}: {codes}")
        return codes
    except Exception as e:
        logger.error(f"Ошибка при анализе {url}: {e}")
        return []


def get_recent_articles():
    """Берем recentArticles из test news"""
    try:
        logger.info("Запрашиваю тестовую новость...")
        resp = requests.get(LOTRO_TEST_NEWS, timeout=10)
        logger.info(f"Статус: {resp.status_code}")

        match = re.search(
            r"recentArticles\s*:\s*(\[[^\]]+\])",
            resp.text
        )
        if not match:
            logger.warning("❌ JSON recentArticles не найден")
            return []

        data = json.loads(match.group(1))
        return [
            "https://www.lotro.com" + item["url"]
            for item in data
        ]

    except Exception as e:
        logger.error(f"Ошибка загрузки recentArticles: {e}")
        return []


async def send_code(bot: Bot, code: str, url: str):
    text = (
        f"🎁 Новый промокод LOTRO!\n"
        f"Код: <b>{code}</b>\n"
        f"Новость: {url}"
    )
    await bot.send_message(
        TARGET_CHAT_ID,
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
    )


# ---------------------------------------- #
#           Основная логика
# ---------------------------------------- #
async def check_promos(bot: Bot):
    logger.info("🔍 Старт проверки LOTRO промокодов...")

    sent_codes = load_sent_codes()
    found_new = False

    urls = get_recent_articles()
    if not urls:
        logger.warning("Новостей не найдено")
        await bot.send_message(
            TARGET_CHAT_ID,
            "ℹ️ Новостей не найдено.",
        )
        return

    logger.info(f"📄 URLs: {len(urls)}")

    for url in urls:
        codes = analyze_article(url)
        for code in codes:
            if code not in sent_codes:
                sent_codes.add(code)
                found_new = True
                await send_code(bot, code, url)

    save_sent_codes(sent_codes)

    if not found_new:
        await bot.send_message(
            TARGET_CHAT_ID,
            "ℹ️ Новых промокодов LOTRO не найдено."
        )


# ---------------------------------------- #
#          Telegram handlers
# ---------------------------------------- #
async def cmd_check(update, context):
    await update.message.reply_text("🕵️ Проверяю новости LOTRO на промокоды...")
    await check_promos(context.bot)


# ---------------------------------------- #
#                MAIN
# ---------------------------------------- #
def main():
    mode = os.getenv("MODE", "BOT")  # BOT / CI
    bot = Bot(BOT_TOKEN)

    if mode == "CI":
        # Single run mode
        logger.info("🚀 MODE=CI → разовая проверка")
        import asyncio
        asyncio.run(check_promos(bot))
        return

    # BOT poll mode
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("check_lotro", cmd_check))

    logger.info("🤖 Бот запущен и ожидает команды /check_lotro")
    application.run_polling()


if __name__ == "__main__":
    main()
