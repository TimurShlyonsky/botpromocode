import json
from pathlib import Path

DATA_PATH = Path("data/promo_codes.json")


def load_codes() -> list[dict]:
    if DATA_PATH.exists():
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return []


def save_codes(codes: list[dict]):
    DATA_PATH.write_text(json.dumps(codes, ensure_ascii=False, indent=2), encoding="utf-8")
