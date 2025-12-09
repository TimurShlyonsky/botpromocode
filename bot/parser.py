import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import re

BASE_URL = "https://www.lotro.com"

# Слова, которые выглядят как коды, но не являются ими
BLACKLIST = {"CODE", "FREE", "HAS", "IS", "OF", "FOR", "CAN", "WILL", "THROUGH"}


def is_valid_code(code: str) -> bool:
    """Фильтруем ложные срабатывания."""
    if len(code) < 6:
        return False
    if code in BLACKLIST:
        return False
    if not re.match(r"^[A-Z0-9]+$", code):
        return False
    return True


def get_month_news(year: int, month: int) -> list[str]:
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"📂 Архив: {url}")

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except Exception:
        return []

    text = response.text

    # JSON news list
    match = re.search(r"window\.SSG\.archive\.articles\s*=\s*(\[[\s\S]*?\]);",
                      text)
    if not match:
        print("⚠️ JSON не найден")
        return []

    try:
        entries = json.loads(match.group(1))
    except Exception:
        print("⚠️ JSON parse error")
        return []

    links = set()
    for e in entries:
        href = e.get("url") or e.get("pageName")
        if not href:
            continue
        if not href.startswith("/"):
            href = "/" + href
        if "/news/" not in href:
            href = "/news" + href
        links.add(urljoin(BASE_URL, href))

    print(f"🔗 Найдено ссылок: {len(links)}")
    return sorted(links)


def extract_promo_from_news(url: str):
    """Ищем реальные промокоды в теле статьи."""
    try:
        res = requests.get(url, timeout=20)
        res.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(res.text, "html.parser")

    # Только содержимое самой статьи
    body = soup.select_one(".article-body")
    if not body:
        return []

    text = body.get_text(" ", strip=True)
    text_u = text.upper()

    promos = []

    # Выдёргиваем вариант "Coupon Code: XXX"
    for m in re.finditer(r"(COUPON CODE|USE CODE|PROMO CODE)[:\s]+([A-Z0-9]+)", text_u):
        code = m.group(2).strip().upper()

        if not is_valid_code(code):
            continue

        # Пытаемся найти описание рядом (до 200 символов)
        desc = extract_description(text, code)

        promos.append({
            "code": code,
            "description": desc,
            "url": url
        })

    return promos


def extract_description(full_text: str, code: str) -> str | None:
    """Описание — 100 символов до и после найденного кода."""
    pos = full_text.upper().find(code)
    if pos == -1:
        return None

    start = max(0, pos - 100)
    end = min(len(full_text), pos + len(code) + 100)
    snippet = full_text[start:end]

    # Мини-фильтр описания
    if len(snippet) < 20:
        return None

    if any(key in snippet.upper() for key in ["FREE", "%", "BOOST", "XP"]):
        return " ".join(snippet.split())

    return None


if __name__ == "__main__":
    for url in get_month_news(2025, 12):
        print(extract_promo_from_news(url))
