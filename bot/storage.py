import json
import os

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "promo_codes.json")


def load_codes():
    """Загружаем список уже отправленных кодов."""
    if not os.path.exists(DATA_FILE):
        return []

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("codes", [])
    except Exception:
        return []


def save_codes(codes: list):
    """Сохраняем обновлённый список промокодов."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump({"codes": codes}, f, indent=4, ensure_ascii=False)

