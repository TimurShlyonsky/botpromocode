import time
import re
import logging
from typing import List, Dict
from urllib.parse import urljoin
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


BASE_URL = "https://www.lotro.com"

logger = logging.getLogger(__name__)

# Ищем фразы вида "Coupon Code: ANDIRUN"
CODE_REGEX = re.compile(
    r"(?:COUPON|Coupon)\s*CODE[:\s]+([A-Z0-9\s\-]{4,40})",
    re.I
)


def init_browser() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def extract_codes(text: str) -> List[str]:
    codes: List[str] = []
    for m in CODE_REGEX.finditer(text):
        raw = m.group(1).strip()
        # Берём только первое "слово" после метки (до пробела/переноса)
        first_token = raw.split()[0]
        # Оставляем только допустимые символы
        code = re.sub(r"[^A-Z0-9\-]", "", first_token.upper())
        if 4 <= len(code) <= 20:
            codes.append(code)
    # Убираем дубликаты
    return list(set(codes))


def parse_article(url: str) -> List[Dict]:
    logger.info(f"Parsing article: {url}")

    browser = init_browser()
    browser.get(url)
    time.sleep(4)  # ждём, пока выполнится JS

    soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.quit()

    result: List[Dict] = []

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else "No title"

    date_tag = soup.find("time")
    date = date_tag.get_text(strip=True) if date_tag else None

    text = soup.get_text(" ", strip=True)
    codes = extract_codes(text)

    for code in codes:
        result.append({
            "code": code,
            "title": title,
            "url": url,
            "date": date,
            "found_in": "selenium-text",
        })

    return result


def get_archive_url_for_current_month() -> str:
    now = datetime.utcnow()
    year = now.year
    month = now.month
    # Архив вида /archive/2025/12
    return f"{BASE_URL}/archive/{year}/{month:02d}"


def get_promo_codes() -> List[Dict]:
    promos: List[Dict] = []

    archive_url = get_archive_url_for_current_month()
    logger.info(f"Opening archive: {archive_url}")

    browser = init_browser()
    browser.get(archive_url)
    time.sleep(6)  # ждём загрузку JS и списка статей

    soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.quit()

    urls: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/news/" in href:
            urls.append(urljoin(BASE_URL, href))

    urls = list(set(urls))
    logger.info(f"📰 Found {len(urls)} articles in archive page {archive_url}")

    for url in urls:
        found = parse_article(url)
        promos.extend(found)

    unique = {item["code"]: item for item in promos}
    return list(unique.values())
