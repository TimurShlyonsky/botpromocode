import re
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

BASE_URL = "https://www.lotro.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_month_news(year: int, month: int) -> list[str]:
    """
    Загружает страницу архива месяца и возвращает ссылки только на новости,
    опубликованные в нужном месяце и году.
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        res = requests.get(url, timeout=20, headers=HEADERS)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Archive fetch failed: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    articles = soup.select("article.archive-item")
    print(f"🔎 На странице найдено статей: {len(articles)}")

    links = []

    for art in articles:
        date_el = art.select_one(".metadata__date")
        a_tag = art.select_one("a[href]")
        if not a_tag:
            continue

        href = a_tag["href"]
        full_url = urljoin(BASE_URL, href)

        # Если даты нет — пропускаем
        if not date_el:
            continue

        date_text = date_el.get_text(strip=True)

        # Пример формата: "Dec 4th, 2025"
        try:
            dt = datetime.strptime(date_text, "%b %dth, %Y")
        except:
            continue

        if dt.year == year and dt.month == month:
            links.append(full_url)

    print(f"🎯 Ссылок за месяц: {len(links)}")
    return sorted(set(links))


def extract_promo_from_news(url: str) -> list[dict]:
    """
    Загружает новость и ищет промокоды в тексте.
    Возвращает список объектов: {"code", "title", "url"}
    """
    try:
        res = requests.get(url, timeout=20, headers=HEADERS)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ News fetch failed {url}: {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    title = soup.select_one("h1")
    title_text = title.get_text(strip=True) if title else "Promo"

    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text_upper = text.upper()

    # Наиболее надёжный паттерн: COUPON CODE: XXXXXXX
    matches = re.findall(r"COUPON CODE[:\s]+([A-Z0-9]+)", text_upper)

    results = []
    for code in set(matches):
        if len(code) >= 6:
            results.append({
                "code": code,
                "title": title_text,
                "url": url
            })

    return results
