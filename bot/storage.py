import json
import os

FILE = "data/promo_codes.json"


def load_codes():
    if not os.path.exists(FILE):
        return set()

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {item["code"] for item in data}
    except:
        return set()


def save_codes(code_objects: list[dict]):
    os.makedirs("data", exist_ok=True)
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(code_objects, f, ensure_ascii=False, indent=2)
