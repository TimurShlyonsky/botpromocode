import re
import json
import requests
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://www.lotro.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_month_news(year: int, month: int) -> list[str]:
    """
    Парсим JSON внутри HTML: window.SSG.archive.articles
    и берём только статьи нужного месяца и года
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        res = requests.get(url, timeout=20, headers=HEADERS)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Archive error: {e}")
        return []

    match = re.search(
        r"window\.SSG\.archive\.articles\s*=\s*(\[[^\]]*\])",
        res.text,
        flags=re.S,
    )
    if not match:
        print("❌ JSON archive not found")
        return []

    try:
        articles = json.loads(match.group(1))
    except:
        print("❌ JSON parse failed")
        return []

    print(f"🔗 Всего статей в JSON: {len(articles)}")

    result = []
    for art in articles:
        link = art.get("link")
        date_str = art.get("date")

        if not link or not date_str:
            continue

        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            continue

        if dt.year == year and dt.month == month:
            full = urljoin(BASE_URL, link)
            result.append(full)

    print(f"🎯 Статей за месяц: {len(result)}")
    return sorted(set(result))


def extract_promo_from_news(url: str) -> list[dict]:
    """
    Ищем промокоды внутри статьи
    """
    try:
        res = requests.get(url, timeout=20, headers=HEADERS)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Load failed {url}: {e}")
        return []

    # Название новости
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", res.text, flags=re.S)
    title = (
        re.sub(r"<.*?>", "", title_match.group(1)).strip()
        if title_match else "Promo"
    )

    # Ищем по всем вариантам COUPON CODE
    codes = re.findall(r"COUPON CODE[:\s]+([A-Z0-9]+)", res.text, flags=re.I)

    result = []
    for code in set(codes):
        if len(code) >= 6:
            result.append({
                "code": code,
                "title": title,
                "url": url
            })

    return result
