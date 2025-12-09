import json
from datetime import datetime
from bot.parser import get_month_news, extract_promo_from_news

DATA_FILE = "data/promo_codes.json"


def load_codes():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_codes(codes):
    with open(DATA_FILE, "w") as f:
        json.dump(codes, f, indent=2)


def run():
    print("🚀 FULL YEAR TEST — 2025")

    all_found = load_codes()
    codes_set = {item["code"] for item in all_found}

    new_found = []

    for month in range(1, 13):
        print(f"\n📅 Месяц: {month:02d}")
        links = get_month_news(2025, month)

        for url in links:
            promos = extract_promo_from_news(url)
            for p in promos:
                if p["code"] not in codes_set:
                    print(f"✨ CODE: {p['code']} — {p['url']}")
                    codes_set.add(p["code"])
                    new_found.append(p)

    if new_found:
        print(f"\n💾 Сохранено новых кодов: {len(new_found)}")
        all_found.extend(new_found)
        save_codes(all_found)
    else:
        print("\nℹ️ Новых кодов нет")


if __name__ == "__main__":
    run()
