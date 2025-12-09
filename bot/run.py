from datetime import datetime
from bot.parser import get_month_news, extract_promo_from_news
from bot.storage import load_codes, save_codes
from bot.send import send_promo


def main():
    current = datetime.utcnow()
    year = current.year
    month = current.month

    print(f"📅 Checking promos for: {year}-{month:02d}")

    links = get_month_news(year, month)
    print(f"🔗 Found {len(links)} news links for this month")

    known_codes = set(load_codes())
    new_found_codes = set()
    updated_codes = list(known_codes)

    total_new_sent = 0

    for link in links:
        promos = extract_promo_from_news(link)
        for promo in promos:
            code = promo["code"]

            if code not in known_codes:
                print(f"✨ New promo found: {code}")
                send_promo(code, promo["description"], promo["url"])
                updated_codes.append(code)
                total_new_sent += 1
            else:
                print(f"⏭ Already sent earlier: {code}")

    if total_new_sent > 0:
        save_codes(updated_codes)
        print(f"💾 Saved {total_new_sent} new codes")
    else:
        print("ℹ️ No new promo codes found")


if __name__ == "__main__":
    main()

