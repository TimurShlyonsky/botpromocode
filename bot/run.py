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
    reactivated_items = []

    for p in promos:
        code = p["code"]
        title = p.get("title") or "Promo"
        url = p.get("url")

        # 🆕 Новый промокод
        if code not in stored_map:
            print(f"✨ NEW: {code}")

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

        # 🔁 Уже был ранее
        else:
            item = stored_map[code]

            # Миграция старых записей
            if "first_seen" not in item:
                item["first_seen"] = today
                item["times_seen"] = 1

            # 🔁 Повторно актуальный
            if item.get("last_seen") != today:
                print(f"🔁 REACTIVATED: {code}")

                item["times_seen"] += 1
                item["last_seen"] = today
                reactivated_items.append(item)

    # 💾 Сохраняем изменения
    if new_items or reactivated_items:
        save_codes(list(stored_map.values()))

    # 📢 Отправка новых
    for n in new_items:
        send(
            n["code"],
            n["title"],
            n["url"]
        )

    # 📢 Отправка повторно актуальных
    for r in reactivated_items:
        send(
            f"🔁 {r['code']}",
            "Промокод снова актуален",
            f"{r['url']}\n\n"
            f"ℹ️ Этот промокод уже встречался ранее\n"
            f"🗓 Впервые обнаружен: {r['first_seen']}"
        )

    if not new_items and not reactivated_items:
        print("ℹ️ No new or reactivated promos found")


if __name__ == "__main__":
    run()
