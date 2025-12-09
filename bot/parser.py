import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://www.lotro.com"


def get_month_news(year: int, month: int) -> list[str]:
    """
    Загружает архивную страницу конкретного месяца и возвращает список ссылок на статьи.
    """
    url = f"{BASE_URL}/archive/{year}/{month:02d}"
    print(f"🔎 Fetching archive: {url}")

    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to load archive page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    # В архиве новости подгружаются динамически через JS
    # Но ссылки есть в HTML внутри темплейта → ищем все <a href>
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Интересуют только новости
        if href.startswith("/news/") or href.startswith("/update-notes/") or href.startswith("/guides/"):
            full_url = urljoin(BASE_URL, href)
            links.add(full_url)

    return sorted(list(links))


if __name__ == "__main__":
    # Тест: получить новости за декабрь 2025
    urls = get_month_news(2025, 12)
    print(f"Найдено {len(urls)} статей:")
    for u in urls:
        print(" -", u)
import re


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

    # Получаем ВСЕ тексты абзацев
    paragraphs = soup.find_all(["p", "div", "span", "li"])

    # Регулярки для разных вариантов написания
    patterns = [
        r"Coupon Code[: ]+([A-Z0-9]+)",
        r"Use Code[: ]+([A-Z0-9]+)",
        r"Use coupon code[: ]+([A-Z0-9]+)",
        r"Code[: ]+([A-Z0-9]+)",
        r"Coupon[: ]+([A-Z0-9]+)",
    ]

    found = []

    for p in paragraphs:
        text = " ".join(p.get_text(" ", strip=True).split())
        if not text:
            continue

        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                code = match.group(1).upper()

                # Ищем описание возле кода (если есть)
                description = extract_description_near(paragraphs, p)

                found.append({
                    "code": code,
                    "description": description,
                    "url": url
                })

    return found


def extract_description_near(paragraphs, code_paragraph):
    """
    Пытаемся найти описание промокода рядом с абзацем где он найден.
    Не более 200 символов. Если описание «шумное» — игнорируем.
    """
    index = paragraphs.index(code_paragraph)

    candidates = []

    # Текущий абзац
    text = code_paragraph.get_text(" ", strip=True)
    cleaned = clean_description_text(text)
    if cleaned:
        candidates.append(cleaned)

    # Абзац выше
    if index > 0:
        above = clean_description_text(paragraphs[index - 1].get_text(" ", strip=True))
        if above:
            candidates.append(above)

    # Абзац ниже
    if index < len(paragraphs) - 1:
        below = clean_description_text(paragraphs[index + 1].get_text(" ", strip=True))
        if below:
            candidates.append(below)

    # Выбираем первый адекватный
    return candidates[0] if candidates else None


def clean_description_text(text: str):
    """
    Фильтруем текст описания:
    - не длиннее 200 символов
    - должен содержать хоть что-то похожее на выгоду/бонус
    """
    if not text or len(text) > 200:
        return None

    # Ключевые слова, которые часто встречаются рядом с кодом
    keywords = ["Free", "%", "off", "Boost", "Bundle", "Coupon", "XP"]

    if any(key.lower() in text.lower() for key in keywords):
        return text

    return None
