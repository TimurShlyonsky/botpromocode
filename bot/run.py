import os
from .parser_selenium import get_promo_codes
from .send import send, send_info
from .storage import load_codes, save_codes


def run():
    print("🚀 Checking promos...")

    stored = load_codes()
    stored_codes = {x["code"] for x in stored}

    promos = get_promo_codes()
    if not promos:
        print("⚠️ No promos found on the site")
        return

    new_items = []

    for p in promos:
        code = p["code"]
        title = p.get("title") or "Promo"
        url = p.get("url")

        if code not in stored_codes:
            print(f"✨ NEW: {code} — {url}")
            stored_codes.add(code)

            new_items.append({
                "code": code,
                "title": title,
                "url": url
            })

    if new_items:
        print(f"💾 Saved {len(new_items)} new codes")
        stored.extend(new_items)
        save_codes(stored)

        for n in new_items:
            send(n["code"], n["title"], n["url"])
    else:
        print("🔔 No new promo codes detected")
        send_info("🔔 Новых промокодов — не обнаружено")

if __name__ == "__main__":
    run()
