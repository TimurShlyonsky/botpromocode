import requests
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://www.lotro.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# ❗ Регулярка для вылавливания JSON со статьями
ARCHIVE_JSON_RE = re.compile(
    r"window\.SSG\.archive\.articles\s*=\s*(\[.*?\]);",
    re.S
)


def get_month_news(year: int, month: int) -> list[dict]:
    """
    Загружает архив месяца и возвращает список статей строго из этого месяца:
    [
        {"url": "...", "title": "..."}
    ]
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load archive: {e}")
        return []

    match = ARCHIVE_JSON_RE.search(resp.text)
    if not match:
        print("⚠️ No JSON found in archive page!")
        return []

    articles = json.loads(match.group(1))
    print(f"🔗 Всего статей в JSON: {len(articles)}")

    filtered = []
    for a in articles:
        date_str = a.get("publishDate")
        if not date_str:
            continue

        # Например: "2025-12-04T12:00:00.000Z"
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except:
            continue

        # ⚠️ ФИЛЬТРУЕМ СТРОГО ПО МЕСЯЦУ
        if dt.year == year and dt.month == month:
            page = a.get("pageName")
            if page:
                filtered.append({
                    "url": f"{BASE_URL}/news/{page}",
                    "title": a.get("title", "No title")
                })

    print(f"🎯 Статей за месяц: {len(filtered)}")
    return filtered


PROMO_RE = re.compile(r"(?:coupon code|use code|use coupon code)[:\s]+([A-Z0-9]+)",
                      re.IGNORECASE)


def extract_promo_from_news(url: str) -> list[dict]:
    """Ищем промокоды внутри статьи"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load page: {url} | {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)

    found = []
    for code in set(PROMO_RE.findall(text)):
        # Фильтр ненужных совпадений (коротких, общих слов)
        if len(code) < 5:
            continue

        found.append({
            "code": code.upper(),
            "url": url
        })

    return found
