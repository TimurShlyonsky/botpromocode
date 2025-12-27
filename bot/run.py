import asyncio
from pathlib import Path

from .parser_selenium import get_promo_codes
from .parser_telegram import get_promo_items_from_telegram
from .send import send, send_info
from .storage import load_codes, save_codes


LOTRO_STORAGE = Path("data/promo_codes.json")
TELEGRAM_STORAGE = Path("data/promo_codes_telegram.json")


def process_promos(promos: list, storage_path: Path):
    """
    Универсальная обработка промокодов:
    - загрузка сохранённых
    - поиск новых
    - сохранение
    - отправка в Telegram
    """
    stored = load_codes(storage_path)
    stored_codes = {x["code"] for x in stored if "code" in x}

    new_items = []

    for p in promos:
        code = p["code"]
        url = p.get("url")

        if code not in stored_codes:
            new_items.append({
                "code": code,
                "url": url,
            })

    if new_items:
        stored.extend(new_items)
        save_codes(stored, storage_path)

        for item in new_items:
            send(item["code"], "Промокод", item["url"])
    else:
        send_info("🔔 Новых промокодов — не обнаружено")


def run():
    print("🚀 Checking LOTRO promos...")
    lotro_promos = get_promo_codes() or []
    process_promos(lotro_promos, LOTRO_STORAGE)

    print("🚀 Checking Telegram promos...")
    try:
        telegram_promos = asyncio.run(get_promo_items_from_telegram())
        process_promos(telegram_promos, TELEGRAM_STORAGE)
    except Exception as e:
        print(f"⚠️ Telegram parser failed: {e}")


if __name__ == "__main__":
    run()
