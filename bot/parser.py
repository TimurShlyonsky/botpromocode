import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import json

BASE_URL = "https://www.lotro.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

# Слова, которые НЕ могут быть промокодами
BLACKLIST = {"IS", "OF", "IN", "CODE", "THROUGH", "FOR", "HAS", "WILL"}

# Паттерны поиска
PATTERNS = [
    r"Coupon Code[:\s]+([A-Z0-9]{5,})",
    r"Use Code[:\s]+([A-Z0-9]{5,})",
    r"Use coupon code[:\s]+([A-Z0-9]{5,})",
    r"CODE[:\s]+([A-Z0-9]{5,})",
]


def get_month_news(year: int, month: int) -> list[str]:
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"🔎 Fetching archive: {url}")

    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except:
        print("❌ Ошибка загрузки архива")
        return []

    # Ищем JSON с новостями
    match = re.search(r"window\.SSG\.archive\.articles\s*=\s*(\[.*?\]);",
                      resp.text, re.S)
    if not match:
        print("⚠️ JSON архива не найден")
        return []

    articles = json.loads(match.group(1))

    urls = []
    for a in articles:
        if "pageName" in a:
            urls.append(urljoin(BASE_URL, f"/news/{a['pageName']}"))

    print(f"🔗 Найдено ссылок: {len(urls)}")
    return urls


def extract_promo_from_news(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except:
        print(f"⚠️ Пропуск (404?): {url}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else "LOTRO News"

    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text_up = text.upper()

    found = set()

    for pattern in PATTERNS:
        matches = re.findall(pattern, text_up)
        for m in matches:
            if len(m) >= 5 and m not in BLACKLIST:
                found.add(m)

    results = []
    for code in sorted(found):
        results.append({
            "code": code,
            "url": url,
            "title": title
        })

    return results
