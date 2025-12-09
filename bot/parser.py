import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.lotro.com"
NEWS_PREFIX = f"{BASE_URL}/news/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Фильтруем слова, которые выглядят как "коды", но ими не являются
BAD_CODES = {"UPDATE", "REMINDER", "THROUGH", "CODE", "FOR", "IS", "OF", "IN", "HAS", "FREE", "WILL"}


def fetch_archive_news(year: int, month: int) -> list[str]:
    """
    Достаём JSON-информацию о новостях месяца.
    Возвращаем список полноценных URL.
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Ошибка загрузки архива: {e}")
        return []

    # Ищем JSON с новостями на архивной странице
    match = re.search(r"window\.SSG\.archive\.articles\s*=\s*(\[[^\]]+\])", res.text)
    if not match:
        print("⚠️ JSON со списком новостей не найден!")
        return []

    try:
        articles = json.loads(match.group(1))
    except Exception as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return []

    urls = []
    for a in articles:
        page = a.get("pageName")
        if page:
            urls.append(NEWS_PREFIX + page)

    print(f"🔗 Найдено ссылок: {len(urls)}")
    return urls


def extract_promo_from_news(url: str) -> list[dict]:
    """
    Скачиваем текст новости и ищем промокоды.
    Возвращаем список объектов:
    {
      "code": ...,
      "title": ...,
      "url": ...,
      "description": ...
    }
    """
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
    except Exception as e:
        print(f"⚠️ Пропускаем {url} — ошибка {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "LOTRO News"

    # Основной текст новости
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text_up = text.upper()

    # Ищем строку вида: COUPON CODE: ANDIRUN
    matches = re.findall(
        r"(?:COUPON CODE|USE CODE|USE COUPON CODE|CODE|COUPON)[:\s]+([A-Z0-9]+)",
        text_up
    )

    found = []
    for code in matches:
        code = code.strip().upper()

        if len(code) < 5:
            continue
        if code in BAD_CODES:
            continue

        found.append({
            "code": code,
            "title": title,
            "url": url,
            "description": extract_near_description(text, code),
        })

    if found:
        print(f"✨ Найдено в {url}: {[f['code'] for f in found]}")
    return found


def extract_near_description(full_text: str, code: str):
    """
    Простейший поиск описания — предложение, содержащее код.
    Ограничиваем длину, чтобы не тащить всю статью.
    """
    sentences = re.split(r"[.!?]", full_text)
    for s in sentences:
        if code in s.upper():
            s = s.strip()
            if 10 <= len(s) <= 200:
                return s
    return None
