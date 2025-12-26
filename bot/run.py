from .parser_selenium import get_promo_codes
from .send import send


def run():
    print("🚀 Checking promos...")

    promos = get_promo_codes()
    if not promos:
        print("⚠️ No promos found on the site")

        send(
            "🔔",
            "Промокоды",
            "На этой неделе новых промокодов не найдено"
        )
        return

    latest = promos[0]  # самый свежий промокод

    print(f"✨ LATEST: {latest['code']}")

    send(
        latest["code"],
        latest.get("title") or "Promo",
        latest.get("url")
    )


if __name__ == "__main__":
    run()
