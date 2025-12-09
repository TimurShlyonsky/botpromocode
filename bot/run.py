from datetime import datetime
from .parser import get_month_news, extract_promo_from_news
from .storage import load_codes, save_codes
from .send import send_message

YEAR = datetime.now().year
MONTH = datetime.now().month


def run():
    print(f"🚀 Checking promos for {YEAR}-{MONTH:02d}")

    saved = load_codes()
    print(f"📁 Already saved: {len(saved)}")

    urls = get_month_news(YEAR, MONTH)
    if not urls:
        print("⚠️ No URLs this month")
        return

    all_found = []
    new_found = []

    for url in urls:
        promos = extract_promo_from_news(url)
        if not promos:
            continue

        for item in promos:
            all_found.append(item)

            if item["code"] not in saved:
                new_found.append(item)
                saved.add(item["code"])
                print(f"✨ NEW: {item['code']} — {url}")
                send_message(
                    f"✨ Новый промокод: <b>{item['code']}</b>\n"
                    f"📰 <a href=\"{item['url']}\">{item['title']}</a>"
                )

    if all_found:
        save_codes(all_found)

    print(f"💾 Saved: {len(all_found)} total | {len(new_found)} new")


if __name__ == "__main__":
    run()
