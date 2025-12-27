import os
import asyncio
from pathlib import Path

from .parser_selenium import get_promo_codes
from .send import send, send_info
from .storage import load_codes, save_codes

LOTRO_STORAGE = Path("data/promo_codes.json")
TELEGRAM_STORAGE = Path("data/promo_codes_telegram.json")


def process_promos(promos: list, storage_path: Path) -> bool:
    stored = load_codes(storage_path)
    stored_codes = {x["code"] for x in stored if "code" in x}

    new_items = []

    for promo in promos:
        code = promo["code"]
        url = promo.get("url")

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

        return True

    return False


def run_lotro():
    promos = get_promo_codes() or []
    has_new = process_promos(promos, LOTRO_STORAGE)

    if not has_new:
        send_info("🔔 [LOTRO] Новых промокодов — не обнаружено")


def run_telegram():
    # ⚠️ импорт ТОЛЬКО здесь
    from .parser_telegram import get_promo_items_from_telegram

    promos = asyncio.run(get_promo_items_from_telegram())
    has_new = process_promos(promos, TELEGRAM_STORAGE)

    if not has_new:
        send_info("🔔 [Tarkov] Новых промокодов — не обнаружено")


def run():
    source = os.getenv("SOURCE", "all").lower()

    if source == "lotro":
        run_lotro()
        return

    if source == "telegram":
        run_telegram()
        return

    # fallback (на будущее, сейчас не используется)
    run_lotro()
    run_telegram()


if __name__ == "__main__":
    run()
