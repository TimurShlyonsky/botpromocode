import os
import time
import re
import json
import logging
from typing import List, Dict
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup


BASE_URL = "https://www.lotro.com"
ARCHIVE_URL = urljoin(BASE_URL, "/archive")

logger = logging.getLogger(__name__)

CODE_REGEX = re.compile(
    r"(?:COUPON|Coupon)\s*CODE[:\s]+([A-Z0-9\-]{4,30})",
    re.I
)


def init_browser() -> webdriver.Chrome:
    options = Options()
    options.binary_location = os.getenv("CHROME_PATH")  # Указываем путь к браузеру
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")

    service = Service(os.getenv("CHROMEDRIVER_PATH"))  # Указываем драйвер

    return webdriver.Chrome(service=service, options=options)


def extract_codes(text: str) -> List[str]:
    return list(set(m.group(1).strip().upper() for m in CODE_REGEX.finditer(text)))


def parse_article(url: str) -> List[Dict]:
    logger.info(f"Parsing article: {url}")

    browser = init_browser()
    browser.get(url)
    time.sleep(3)

    soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.quit()

    result = []

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
            "found_in": "selenium-rendered"
        })

    return result


def get_promo_codes() -> List[Dict]:
    promos = []

    browser = init_browser()
    browser.get(ARCHIVE_URL)
    time.sleep(5)

    soup = BeautifulSoup(browser.page_source, "html.parser")
    browser.quit()

    # Ищем ссылки на статьи по паттерну страниц новостей
    urls = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/news/" in href:
            urls.append(urljoin(BASE_URL, href))

    urls = list(set(urls))
    logger.info(f"Found {len(urls)} articles")

    for url in urls:
        found = parse_article(url)
        promos.extend(found)

    unique = {item["code"]: item for item in promos}
    return list(unique.values())
