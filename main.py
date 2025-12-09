import os
import re
import json
import logging
import datetime as dt
from typing import List, Tuple, Set

import requests
from bs4 import BeautifulSoup
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ---------------------- ЛОГИРОВАНИЕ ----------------------

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------- НАСТРОЙКИ ------------------------

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Слова-шум, которые могут попадаться при общем поиске ВСЕХ капслок-слов.
# На ЯВНЫЕ паттерны вида "COUPON CODE: ABC123" этот список не влияет.
GENERIC_BLACKLIST = {
    "UPDATE",
    "REMINDER",
    "THROUGH",
    "ONLINE",
    "COUPON",
}

ARCHIVE_URL_TEMPLATE = "https://www.lotro.com/archive/{year}/{month:02d}"
SENT_CODES_FILE = "sent_codes.json"

# ------------------ ХРАНЕНИЕ ОТПРАВЛЕННЫХ КОДОВ ------------------


def load_sent_codes() -> Set[str]:
    """Читаем уже найденные и отправленные промокоды из файла."""
    if not os.path.exists(SENT_CODES_FILE):
        return set()
    try:
        with open(SENT_CODES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data)
    except Exception as e:
        logger.warning("Не удалось прочитать %s: %s", SENT_CODES_FILE, e)
        return set()


def save_sent_codes(codes: Set[str]) -> None:
    """Сохраняем промокоды в файл, чтобы не дублировать."""
    try:
        with open(SENT_CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(codes), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("Не удалось записать %s: %s", SENT_CODES_FILE, e)


# ------------------ ПАРСИНГ АРХИВА LOTRO ------------------


def fetch_article_urls_from_archive(year: int | None = None,
                                    month: int | None = None) -> List[str]:
    """
    Берём список статей за указанный месяц из /archive/YYYY/MM
    и строим реальные URL статей.
    """
    if year is None or month is None:
        now = dt.datetime.now(ZoneInfo("Europe/London"))
        year = now.year
        month = now.month

    archive_url = ARCHIVE_URL_TEMPLATE.format(year=year, month=month)
    logger.info("Запрашиваю архив LOTRO: %s", archive_url)

    try:
        resp = requests.get(archive_url, headers=HEADERS, timeout=20)
    except Exception as e:
        logger.error("Ошибка запроса архива %s: %s", archive_url, e)
        return []

    if resp.status_code != 200:
        logger.warning("Архив вернул статус %s", resp.status_code)
        return []

    html = resp.text

    # Ищем JSON в window.SSG.archive.articles = [ ... ];
    match = re.search(
        r"window\.SSG\.archive\.articles\s*=\s*(\[\{.*?\}\])\s*;",
        html,
        re.S,
    )
    if not match:
        logger.warning("❌ Не найден блок window.SSG.archive.articles в архиве.")
        return []

    try:
        articles = json.loads(match.group(1))
    except Exception as e:
        logger.error("Не удалось распарсить JSON из archive.articles: %s", e)
        return []

    urls: List[str] = []

    for item in articles:
        page_name = item.get("pageName")
        item_type = item.get("type")
        locale = item.get("locale")

        if not page_name:
            continue
        # Обычно промокоды лежат в новостях, но на всякий случай
        # различим типы, чтобы не получать 404, где это можно избежать.
        if item_type in {"wgt_update_notes", "update-notes"}:
            prefix = "update-notes"
        elif item_type in {"wgt_guide", "guide"}:
            prefix = "guides"
        else:
            # global_newscast, news, wgt_article и т.п. — через /news/
            prefix = "news"

        url = f"https://www.lotro.com/{prefix}/{page_name}"
        urls.append(url)

    logger.info("📄 Статей в архиве за %02d.%d: %d", month, year, len(urls))

    if urls:
        logger.info("🔗 Примеры ссылок из архива:")
        for u in urls[:10]:
            logger.info(" - %s", u)

    return urls


# ------------------ ВЫДЕЛЕНИЕ ПРОМОКОДОВ ------------------


def extract_coupon_codes(html: str) -> List[str]:
    """
    Ищем промокоды внутри .article-body.
    Сначала — по явным паттернам COUPON CODE, затем — общий капслок-поиск.
    """
    soup = BeautifulSoup(html, "html.parser")
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text_upper = text.upper()

    codes: set[str] = set()

    # 1) Явные паттерны купонов. Чёрный список тут НЕ применяется.
    explicit_patterns = [
        r"COUPON CODE[:\s]+([A-Z0-9]+)",
        r"COUPON[:\s]+CODE[:\s]+([A-Z0-9]+)",
        r"COUPON[:\s]+([A-Z0-9]+)",
    ]
    for pattern in explicit_patterns:
        matches = re.findall(pattern, text_upper)
        codes.update(matches)

    # 2) Общий капслок-поиск — чтобы подстраховаться,
    # но тут уже применяем GENERIC_BLACKLIST.
    generic_matches = re.findall(r"\b[A-Z0-9]{6,}\b", text_upper)
    for token in generic_matches:
        if token in GENERIC_BLACKLIST:
            continue
        # если уже нашли этим же паттерном — не дублируем
        if token not in codes:
            codes.add(token)

    # Фильтрация по длине на всякий случай
    filtered = {c for c in codes if len(c) >= 6}
    return sorted(filtered)


# ------------------ ОСНОВНАЯ ПРОВЕРКА LOTRO ------------------


def run_lotro_check() -> Tuple[str, List[Tuple[str, str]]]:
    """
    Основная логика проверки:
    - берём список статей за текущий месяц из архива;
    - ищем промокоды в каждой;
    - сравниваем с уже отправленными;
    - сохраняем новые в sent_codes.json;
    - возвращаем текстовый отчёт и список новых (код, URL).
    """
    logger.info("🔍 Старт проверки LOTRO промокодов...")

    urls = fetch_article_urls_from_archive()
    if not urls:
        msg = "❌ Не удалось получить список статей из архива LOTRO."
        logger.warning(msg)
        return msg, []

    sent_codes = load_sent_codes()
    logger.info("Уже известные коды: %s", ", ".join(sorted(sent_codes)) or "нет")

    new_found: List[Tuple[str, str]] = []

    logger.info("🔍 Начинаю анализ страниц...")

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
        except Exception as e:
            logger.warning("Ошибка при запросе %s: %s", url, e)
            continue

        if resp.status_code != 200:
            logger.info("⚠️ Пропускаю (HTTP %s): %s", resp.status_code, url)
            continue

        codes = extract_coupon_codes(resp.text)
        if codes:
            logger.info("🧩 Найдено в %s: %s", url, codes)
            for code in codes:
                if code not in sent_codes:
                    sent_codes.add(code)
                    new_found.append((code, url))
        else:
            logger.info("… нет промокодов → %s", url)

    save_sent_codes(sent_codes)

    if new_found:
        lines = ["🔥 Новые промокоды:"]
        for code, url in new_found:
            lines.append(f"  ✔ {code} — {url}")
        message = "\n".join(lines)
    else:
        message = "ℹ️ Новых промокодов нет."

    logger.info("Результат проверки: %s", message.replace("\n", " | "))
    return message, new_found


def run_cli() -> None:
    """
    Простой запуск из консоли (и для MODE=CI):
    выводит результат в stdout.
    """
    text, _ = run_lotro_check()
    print("\n===== РЕЗУЛЬТАТ ПРОВЕРКИ LOTRO =====")
    print(text)


# ------------------ TELEGRAM-БОТ ------------------


async def check_lotro_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /check_lotro — ручная проверка и лог в чат."""
    chat_id = update.effective_chat.id if update.effective_chat else None
    logger.info("Команда /check_lotro от chat_id=%s", chat_id)

    if update.message:
        await update.message.reply_text(
            "🔍 Запускаю проверку промокодов LOTRO, подожди пару секунд..."
        )

    text, _ = run_lotro_check()

    if update.message:
        await update.message.reply_text(text)


async def lotro_friday_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Авто-проверка по пятницам.
    Отправляет результат в CHANNEL_ID (из env) или, если его нет, просто логирует.
    """
    logger.info("⏰ Запуск автопроверки LOTRO (пятница 12:00 Europe/London)")

    text, _ = run_lotro_check()
    prefix = "🤖 Автопроверка LOTRO промокодов (пятница 12:00)\n\n"
    full_text = prefix + text

    chat_id_env = os.getenv("CHANNEL_ID")
    if not chat_id_env:
        logger.warning("CHANNEL_ID не задан, отправка в Telegram пропущена.")
        return

    try:
        # CHANNEL_ID может быть как числом (чат/канал), так и @username
        chat_id: int | str
        try:
            chat_id = int(chat_id_env)
        except ValueError:
            chat_id = chat_id_env

        await context.bot.send_message(chat_id=chat_id, text=full_text)
        logger.info("Сообщение автопроверки отправлено в chat_id=%s", chat_id_env)
    except Exception as e:
        logger.error("Не удалось отправить сообщение автопроверки в Telegram: %s", e)


def main() -> None:
    mode = os.getenv("MODE", "").upper()

    # ---------------- MODE=CI ----------------
    # Для GitHub Actions/CI: один раз проверить и завершиться.
    if mode == "CI":
        logger.info("Режим MODE=CI: однократная проверка и выход.")
        run_cli()
        return

    # ---------------- Обычный режим бота ----------------

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError(
            "Не задан BOT_TOKEN в переменных окружения. "
            "Получите токен у @BotFather и задайте BOT_TOKEN."
        )

    application = Application.builder().token(bot_token).build()

    # Команда для ручной проверки
    application.add_handler(CommandHandler("check_lotro", check_lotro_command))

    # Планировщик: каждую пятницу в 12:00 по Europe/London
    job_queue = application.job_queue
    london_tz = ZoneInfo("Europe/London")

    # 0 = Monday ... 4 = Friday
    job_queue.run_daily(
        lotro_friday_job,
        time=dt.time(hour=12, minute=0, tzinfo=london_tz),
        days=(4,),
        name="lotro_friday_noon",
    )

    logger.info("Бот запущен. Команда: /check_lotro")
    logger.info("⏰ Автопроверка: каждый Friday 12:00 (Europe/London).")

    application.run_polling()


if __name__ == "__main__":
    main()
