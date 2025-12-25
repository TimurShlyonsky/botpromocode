import os
from datetime import date
from .parser_selenium import get_promo_codes
from .send import send
from .storage import load_codes, save_codes


def run():
    print("🚀 Checking promos...")

    today = date.today().isoformat()

    stored = load_codes()
    stored_map = {x["code"]: x for x in stored}

    promos = get_promo_codes()
    if not promos:
        print("⚠️ No promos found on the site")
        return

    new_items = []

    for p in promos:
        code = p["code"]
        title = p.get("title") or "Promo"
        url = p.get("url")

        if code not in stored_map:
            print(f"✨ NEW: {code} — {url}")

            item = {
                "code": code,
                "title": title,
                "url": url,
                "first_seen": today,
                "last_seen": today,
                "times_seen": 1
            }

            stored_map[code] = item
            new_items.append(item)

        else:
            item = stored_map[code]

            # Миграция старых записей
            if "first_seen" not in item:
                item["first_seen"] = today
                item["times_seen"] = 1

            item["last_seen"] = today

    if new_items:
        print(f"💾 Saved {len(new_items)} new codes")
        save_codes(list(stored_map.values()))

        for n in new_items:
            send(n["code"], n["title"], n["url"])
    else:
        print("ℹ️ No new promos found")


if __name__ == "__main__":
    run()
