import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.lotro.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9"
}

# Слова, которые НЕ могут быть кодами
BAD_CODES = {"OF", "IS", "HAS", "CODE", "FREE", "THROUGH", "FOR"}

# Минимальная длина кода
MIN_LEN = 6


def get_month_news(year: int, month: int) -> list[str]:
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        page = requests.get(url, headers=HEADERS, timeout=15)
        page.raise_for_status()
    except Exception:
        return []

    # JSON внутри window.SSG.archive.articles = [...]
    match = re.search(
        r"window\.SSG\.archive\.articles\s*=\s*(\[.*?\]);",
        page.text, re.S
    )
    if not match:
        print("⚠️ JSON архив не найден!")
        return []

    articles = json.loads(match.group(1))

    links = [
        urljoin(BASE_URL, a["slug"])
        for a in articles
        if a.get("slug", "").startswith("/news/")
    ]

    print(f"🔗 Найдено ссылок: {len(links)}")
    return links


def extract_promo_from_news(url: str):
    try:
        res = requests.get(url, headers=HEADERS, timeout=20)
        res.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    # title статьи
    title = soup.title.get_text(strip=True) if soup.title else "LOTRO News"

    # Текст новости
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text_upper = text.upper()

    # Ищем коды
    codes = re.findall(r"COUPON\s+CODE[:\s]+([A-Z0-9]+)", text_upper)

    # Фильтруем
    clean = []
    for c in codes:
        if len(c) < MIN_LEN:
            continue
        if c in BAD_CODES:
            continue
        clean.append({
            "code": c,
            "url": url,
            "title": title,
            "description": None
        })

    return clean
