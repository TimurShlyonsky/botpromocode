import os
import json
import re
import html
from datetime import datetime, time
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# ==========================
# НАСТРОЙКИ
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
# ID чата или канала, куда слать результаты (например, -1001234567890)
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID", "123456789"))

SENT_CODES_FILE = "sent_codes.json"

# Стабильная новость, в которой на странице есть window.SSG.news.recentArticles
LOTRO_NEWS_SOURCE_URL = "https://www.lotro.com/news/lotro-bonus-120425-en"

# Таймзона для автопроверки (пятница 12:00)
TZ = ZoneInfo("Europe/London")

# ==========================
# УТИЛИТЫ ДЛЯ ХРАНИЛИЩА КОДОВ
# ==========================


def load_sent_codes() -> dict:
    """Загружаем уже отправленные коды из файла."""
    if not os.path.exists(SENT_CODES_FILE):
        return {}
    try:
        with open(SENT_CODES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        print(f"⚠️ Не удалось прочитать {SENT_CODES_FILE}: {e}")
        return {}


def save_sent_codes(data: dict) -> None:
    """Сохраняем коды в файл."""
    try:
        with open(SENT_CODES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Не удалось записать {SENT_CODES_FILE}: {e}")


# ==========================
# СЕТЕВЫЕ ЗАПРОСЫ
# ==========================

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36"),
    "Accept":
    "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":
    "en-US,en;q=0.9",
    "Referer":
    "https://www.lotro.com/home",
}


def http_get(url: str) -> str | None:
    """Обёртка над requests.get с логированием."""
    print(f"Запрашиваю: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        print("Статус:", resp.status_code)
        if resp.status_code != 200:
            return None
        return resp.text
    except Exception as e:
        print(f"❌ Ошибка запроса {url}: {e}")
        return None


# ==========================
# ПАРСИНГ СПИСКА НОВОСТЕЙ
# ==========================


def discover_recent_article_urls() -> list[str]:
    """
    Берём любую живую новость LOTRO, вытаскиваем из неё
    window.SSG.news.recentArticles и получаем список URL статей.
    """
    print("🕵️ Проверяю новости LOTRO на промокоды...")
    html_text = http_get(LOTRO_NEWS_SOURCE_URL)
    if not html_text:
        print("❌ Не удалось получить страницу с recentArticles.")
        return []

    # Вырезаем JSON из window.SSG.news.recentArticles = [...]
    m = re.search(
        r"window\.SSG\.news\.recentArticles\s*=\s*(\[\{.*?}]);",
        html_text,
        flags=re.DOTALL,
    )
    if not m:
        print("❌ JSON recentArticles не найден!")
        return []

    json_str = m.group(1)
    try:
        articles = json.loads(json_str)
    except Exception as e:
        print(f"❌ Ошибка парсинга recentArticles JSON: {e}")
        return []

    urls: list[str] = []
    for item in articles:
        page_name = item.get("pageName")
        if not page_name:
            continue

        # Практически все статьи доступны по /news/<pageName>
        url = f"https://www.lotro.com/news/{page_name}"
        urls.append(url)

    print(f"📄 Кол-во статей в recentArticles: {len(urls)}\n")
    print("🔗 Примеры найденных ссылок:")
    for u in urls[:10]:
        print(f" - {u}")
    print()
    return urls


# ==========================
# ПАРСИНГ ПРОМОКОДОВ ИЗ ОДНОЙ СТАТЬИ
# ==========================


def extract_article_text(html_text: str) -> str:
    """
    Вытаскиваем осмысленный текст новости:
    - сначала из <script type="application/ld+json"> (articleBody),
    - если не получилось — из <div class="article-body">.
    """
    soup = BeautifulSoup(html_text, "html.parser")

    texts: list[str] = []

    # 1) ld+json блоки с NewsArticle
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            raw = script.string or ""
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, dict) and data.get("@type") == "NewsArticle":
            body = data.get("articleBody") or ""
            if body:
                texts.append(html.unescape(body))

    # 2) Фолбэк на видимую верстку
    if not texts:
        body_div = soup.find("div", class_="article-body")
        if body_div:
            texts.append(body_div.get_text(separator=" ", strip=True))

    return "\n".join(texts)


def extract_promo_codes_from_text(text: str) -> set[str]:
    """
    ВАЖНО: мы не ищем все подряд CAPS-слова.
    Берём только то, что явно помечено как Coupon Code.

    Поддерживаем формы:
    - "Coupon Code: ANDIRUN"
    - "COUPON CODE: DECTRACERY"
    - "Use the Coupon Code EXPLOREOURWORLD through December..."
    - "Coupon code ANDIRUN"
    """
    codes: set[str] = set()
    if not text:
        return codes

    # Нормализуем, но ищем регистронезависимо
    # 1) Прямое "coupon code: XXXXX"
    pattern_coupon_code = re.compile(r"(?i)coupon\s+code[:\s]+([A-Z0-9]{4,})")
    for m in pattern_coupon_code.finditer(text):
        code = m.group(1).upper()
        codes.add(code)

    # 2) "use the coupon code XXXXX"
    pattern_use_coupon = re.compile(
        r"(?i)use\s+the\s+coupon\s+code\s+([A-Z0-9]{4,})")
    for m in pattern_use_coupon.finditer(text):
        code = m.group(1).upper()
        codes.add(code)

    # 3) "COUPON CODE: XXXXX" (практически то же, но пусть будет отдельно)
    pattern_caps_coupon = re.compile(r"(?i)COUPON\s+CODE[:\s]+([A-Z0-9]{4,})")
    for m in pattern_caps_coupon.finditer(text):
        code = m.group(1).upper()
        codes.add(code)

    return codes


def extract_promo_codes_from_article(url: str) -> set[str]:
    """Грузим статью и достаём из неё промокоды по контексту."""
    html_text = http_get(url)
    if not html_text:
        return set()

    article_text = extract_article_text(html_text)
    codes = extract_promo_codes_from_text(article_text)

    if codes:
        print(f"🧩 Найдено промокодов в {url}: {sorted(codes)}")
    else:
        print(f"… нет промокодов → {url}")

    return codes


# ==========================
# ГЛАВНАЯ ЛОГИКА ПРОВЕРКИ
# ==========================


def scrape_lotro_promo_codes() -> dict[str, str]:
    """
    Возвращает словарь {код: url_статьи} для ВСЕХ найденных кодов
    в последних новостях.
    """
    urls = discover_recent_article_urls()
    all_codes: dict[str, str] = {}

    if not urls:
        print("⚠️ Нет URL статей для анализа.")
        return all_codes

    print("🔍 Начинаю анализ страниц...\n")

    for url in urls:
        codes = extract_promo_codes_from_article(url)
        for code in codes:
            # Если вдруг код встречается в нескольких новостях — оставим первую
            all_codes.setdefault(code, url)

    print("\n===== ОБЩИЙ СПИСОК КОДОВ (сырые) =====")
    if not all_codes:
        print("Промокоды не найдены ни в одной статье.")
    else:
        for code, u in all_codes.items():
            print(f"  • {code} — {u}")
    print("======================================\n")

    return all_codes


# ==========================
# BOT / TELEGRAM ЛОГИКА
# ==========================


async def send_result_message(
    context: ContextTypes.DEFAULT_TYPE,
    header: str,
    new_codes: dict[str, str],
    is_manual: bool,
) -> None:
    """Отправляет итоговое сообщение в канал/чат."""
    if new_codes:
        lines = [
            f"🔥 Новые промокоды LOTRO ({'ручная' if is_manual else 'автопроверка'}):"
        ]
        for code, url in new_codes.items():
            lines.append(f"  ✔ {code} — {url}")
    else:
        lines = [
            f"ℹ️ Новых промокодов LOTRO нет. ({'ручная' if is_manual else 'автопроверка'})"
        ]

    text = header + "\n" + "\n".join(lines)

    await context.bot.send_message(
        chat_id=TARGET_CHAT_ID,
        text=text,
        disable_web_page_preview=False,
    )


async def run_lotro_check(context: ContextTypes.DEFAULT_TYPE,
                          is_manual: bool) -> None:
    """
    Общая функция проверки:
    - собирает все текущие коды;
    - сравнивает с сохранёнными;
    - шлёт только новые;
    - обновляет sent_codes.json.
    """
    if is_manual:
        header = "🕵️ Запущена ручная проверка LOTRO на промокоды..."
    else:
        header = "🕵️ Автоматическая проверка LOTRO на промокоды..."

    print(header)

    current_codes = scrape_lotro_promo_codes()

    sent_codes = load_sent_codes()  # {CODE: {...}}
    now_iso = datetime.now(tz=TZ).isoformat(timespec="seconds")

    new_codes: dict[str, str] = {}

    for code, url in current_codes.items():
        if code not in sent_codes:
            new_codes[code] = url
            sent_codes[code] = {
                "url": url,
                "first_seen": now_iso,
            }

    # Сохраняем обновлённый список всех уже отправленных
    save_sent_codes(sent_codes)

    print("===== РЕЗУЛЬТАТ =====")
    if new_codes:
        print("🔥 Новые промокоды:")
        for code, url in new_codes.items():
            print(f"  ✔ {code} — {url}")
    else:
        print("ℹ️ Новых промокодов нет.")
    print("=====================\n")

    await send_result_message(context, header, new_codes, is_manual=is_manual)


# --- Команда /check_lotro ---


async def cmd_check_lotro(update: Update,
                          context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ручной запуск проверки через команду /check_lotro."""
    # Короткий ответ в личку/чат, откуда пришла команда
    if update.effective_chat:
        await update.effective_chat.send_message(
            "✅ Запускаю проверку промокодов LOTRO... Результат придёт в канал."
        )

    await run_lotro_check(context, is_manual=True)


# --- Автопроверка по пятницам ---


async def scheduled_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Джоб для JobQueue: автопроверка по пятницам в 12:00."""
    await run_lotro_check(context, is_manual=False)


# ==========================
# MAIN
# ==========================


def main() -> None:
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(
            "❌ Укажи BOT_TOKEN в коде или через переменную окружения BOT_TOKEN."
        )
        return

    application = (Application.builder().token(BOT_TOKEN).build())

    # Команда /check_lotro
    application.add_handler(CommandHandler("check_lotro", cmd_check_lotro))

    # Планируем джоб: каждую пятницу в 12:00 Europe/London
    job_queue = application.job_queue
    job_queue.run_daily(
        scheduled_job,
        time=time(hour=12, minute=0, tzinfo=TZ),
        days=(4, ),  # 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
        name="lotro_weekly_check",
    )

    print("🤖 Бот запущен. Команда: /check_lotro")
    print("⏰ Автопроверка: каждый Friday 12:00 (Europe/London).")
    application.run_polling()


if __name__ == "__main__":
    main()
