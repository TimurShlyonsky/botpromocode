import os
from datetime import datetime
from .parser import get_month_news, extract_promo_from_news
from .send import send
from .storage import load_codes, save_codes


def run():
    now = datetime.utcnow()
    year = now.year
    month = now.month

    print(f"🚀 Checking promos for {year}-{month:02d}")

    stored = load_codes()
    stored_codes = {x["code"] for x in stored}

    articles = get_month_news(year, month)
    if not articles:
        print("⚠️ No URLs this month")
        return

    new_items = []

    for a in articles:
        url = a["url"]
        promos = extract_promo_from_news(url)

        if promos:
            print(f"✨ Найдено в {url}: {[p['code'] for p in promos]}")

        for p in promos:
            code = p["code"]
            if code not in stored_codes:
                print(f"✨ NEW: {code} — {url}")
                stored_codes.add(code)

                new_items.append({
                    "code": code,
                    "title": a["title"],
                    "url": url
                })

    if new_items:
        print(f"💾 Saved {len(new_items)} codes")
        stored.extend(new_items)
        save_codes(stored)

        for n in new_items:
            send(n["code"], n["title"], n["url"])
    else:
        print("ℹ️ No new promos found")


if __name__ == "__main__":
    run()
