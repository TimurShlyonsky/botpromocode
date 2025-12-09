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
