import re
import json
import logging
from typing import List, Dict
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


BASE_URL = "https://www.lotro.com"
ARCHIVE_URL = urljoin(BASE_URL, "/archive")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BotPromoCode/1.0)"
}

logger = logging.getLogger(__name__)

CODE_REGEX = re.compile(
    r"(?:COUPON|Coupon)\s*CODE[:\s]+([A-Z0-9\-]{4,30})",
    re.I
)


def fetch_html(url: str) -> str | None:
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"HTTP error while requesting {url}: {e}")
        return None


def extract_codes_from_text(text: str) -> List[str]:
    codes = []
    for match in CODE_REGEX.finditer(text):
        code = match.group(1).strip().upper()
        if 4 <= len(code) <= 30:
            codes.append(code)
    return list(set(codes))


def extract_codes_from_jsonld(soup: BeautifulSoup) -> List[str]:
    codes = []
    for script in soup.find_all("script", {"type": "application/ld+json"}):
        try:
            data = json.loads(script.string)
        except Exception:
            continue

        for key in ("articleBody", "alternativeHeadline", "description", "headline"):
            value = data.get(key)
            if not value or not isinstance(value, str):
                continue

            found = extract_codes_from_text(value)
            codes.extend(found)

    return list(set(codes))


def parse_article(url: str) -> List[Dict]:
    html = fetch_html(url)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    result = []

    title_tag = soup.find("h1")
    title = title_tag.get_text(strip=True) if title_tag else None

    date_tag = soup.find("time")
    date = date_tag.get_text(strip=True) if date_tag else None

    image_tag = soup.find("img")
    image_src = urljoin(url, image_tag["src"]) if image_tag and image_tag.get("src") else None

    codes = []

    # 1) JSON-LD
    jsonld_codes = extract_codes_from_jsonld(soup)
    if jsonld_codes:
        codes.extend(jsonld_codes)

    # 2) Article text
    article_tag = soup.find("article")
    text = article_tag.get_text(" ", strip=True) if article_tag else soup.get_text(" ", strip=True)
    body_codes = extract_codes_from_text(text)
    if body_codes:
        codes.extend(body_codes)

    # 3) Title
    if title:
        title_codes = extract_codes_from_text(title)
        if title_codes:
            codes.extend(title_codes)

    codes = list(set(codes))

    for code in codes:
        result.append({
            "code": code,
            "title": title,
            "url": url,
            "date": date,
            "image": image_src,
            "found_in": "jsonld/body/title"
        })

    return result


def parse_archive() -> List[Dict]:
    """
    Извлекает статьи из JS-структуры window.SSG.archive.articles
    """
    html = fetch_html(ARCHIVE_URL)
    if not html:
        return []

    match = re.search(
        r"window\.SSG\.archive\.articles\s*=\s*(\[\s*{.*?}\s*\]);",
        html,
        flags=re.S
    )
    if not match:
        logger.error("JS articles array not found in archive page")
        return []

    try:
        articles_json = json.loads(match.group(1))
    except Exception as e:
        logger.error(f"Failed to parse archive JSON: {e}")
        return []

    articles = []
    for a in articles_json:
        url = a.get("fullUrl") or a.get("url")
        if not url:
            continue
        full_url = urljoin(BASE_URL, url)

        articles.append({
            "url": full_url,
            "title": a.get("title"),
            "summary": a.get("summary"),
            "date": a.get("publishDate")
        })

    return articles


def parse_news_list() -> List[Dict]:
    promos = []
    articles = parse_archive()
    if not articles:
        logger.warning("No articles found in archive.")
        return []

    for a in articles:
        url = a["url"]
        found = parse_article(url)
        if found:
            logger.info(f"Found promo codes in {url}")
            for item in found:
                if not item.get("title"):
                    item["title"] = a.get("title")
                if not item.get("date"):
                    item["date"] = a.get("date")
                promos.append(item)

    unique = {item["code"]: item for item in promos}
    return list(unique.values())


def get_promo_codes() -> List[Dict]:
    try:
        return parse_news_list()
    except Exception as e:
        logger.exception(f"Error in promo parsing: {e}")
        return []
