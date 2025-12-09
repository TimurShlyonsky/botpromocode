import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re

BASE_URL = "https://www.lotro.com"


def get_month_news(year: int, month: int) -> list[str]:
    """
    Загружает архивную страницу месяца и извлекает ссылки на статьи
    из встроенного JSON (newsEntries), т.к. контент подгружается JS.
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"🔎 Fetching archive: {url}")

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load archive page: {e}")
        return []

    # Ищем JSON массив newsEntries
    match = re.search(r'"newsEntries":\s*(\[[^\]]*\])', response.text, flags=re.DOTALL)
    if not match:
        print("⚠️ No newsEntries found on page.")
        return []

    try:
        entries = json.loads(match.group(1))
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        return []

    links = set()

    for entry in entries:
        href = entry.get("url")
        if href:
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)

    print(f"🔗 Found {len(links)} news links for this month")
    return sorted(list(links))


def extract_promo_from_news(url: str):
    """
    Загружает новость и ищет промокоды.
    Возвращает список объектов: {"code", "description", "url"}
    """
    try:
        res = requests.get(url, timeout=20)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load news page: {url} | {e}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    # Сбор всех текстовых блоков, где могут быть коды
    paragraphs = soup.find_all(["p", "div", "span", "li"])

    patterns = [
        r"Coupon Code[: ]+([A-Z0-9]+)",
        r"Use Code[: ]+([A-Z0-9]+)",
        r"Use coupon code[: ]+([A-Z0-9]+)",
        r"Code[: ]+([A-Z0-9]+)",
        r"Coupon[: ]+([A-Z0-9]+)"
    ]

    found = []

    for i, p in enumerate(paragraphs):
        text = " ".join(p.get_text(" ", strip=True).split())
        if not text:
            continue

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                code = match.group(1).upper()
                description = extract_description_near(paragraphs, i)

                found.append({
                    "code": code,
                    "description": description,
                    "url": url
                })

    return found


def extract_description_near(paragraphs, index: int):
    """
    Ищем текст-описание рядом с абзацем кода.
    """
    candidates = []

    def add_candidate(i):
        if 0 <= i < len(paragraphs):
            t = clean_description_text(paragraphs[i].get_text(" ", strip=True))
            if t:
                candidates.append(t)

    add_candidate(index)
    add_candidate(index - 1)
    add_candidate(index + 1)

    return candidates[0] if candidates else None


def clean_description_text(text: str):
    """
    Удаляем шум, оставляем только полезное описание.
    """
    if not text or len(text) > 200:
        return None

    keywords = ["Free", "%", "off", "Boost", "Bundle", "XP", "Tome", "Item"]

    if any(key.lower() in text.lower() for key in keywords):
        return text

    return None


if __name__ == "__main__":
    # Тест локального запуска – можно менять дату
    links = get_month_news(2025, 12)
    print("News links:", links)
    for link in links:
        promos = extract_promo_from_news(link)
        if promos:
            print("FOUND:", promos)
