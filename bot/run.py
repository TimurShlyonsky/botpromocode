import json
from bot.parser import get_month_news, extract_promo_from_news

DATA_FILE = "data/promo_codes.json"


def load_codes():
    """
    Загружаем уже найденные коды.
    Поддерживаем два формата:
    1) ["ANDIRUN", "EXPLOREOURWORLD", ...]       # старый формат (список строк)
    2) [{"code": "...", "description": "...", ..} # новый формат (список объектов)
    """
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return []

    # Новый формат: список словарей с ключом "code"
    if isinstance(data, list) and all(isinstance(x, dict) and "code" in x for x in data):
        return data

    # Старый формат: список строк
    if isinstance(data, list) and all(isinstance(x, str) for x in data):
        return [{"code": c, "description": None, "url": None} for c in data]

    # Непонятный формат — начинаем с нуля
    return []


def save_codes(codes):
    with open(DATA_FILE, "w") as f:
        json.dump(codes, f, indent=2, ensure_ascii=False)


def run():
    print("🚀 FULL YEAR TEST — 2025")

    all_found = load_codes()
    print(f"📁 Уже было сохранено кодов: {len(all_found)}")

    codes_set = {item["code"] for item in all_found}
    new_found = []

    # Проходим по всем месяцам 2025
    for month in range(1, 13):
        print(f"\n📅 Месяц: {month:02d}")
        links = get_month_news(2025, month)

        for url in links:
            promos = extract_promo_from_news(url)
            for p in promos:
                code = p["code"]
                if code not in codes_set:
                    print(f"✨ CODE: {code} — {p['url']}")
                    codes_set.add(code)
                    new_found.append(p)

    if new_found:
        print(f"\n💾 Сохранено новых кодов: {len(new_found)}")
        all_found.extend(new_found)
        save_codes(all_found)
    else:
        print("\nℹ️ Новых кодов нет")


if __name__ == "__main__":
    run()
