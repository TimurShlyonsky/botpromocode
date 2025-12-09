import json
from pathlib import Path

DATA_PATH = Path("data/promo_codes.json")


def load_codes() -> list:
    """
    Загружаем сохранённые коды
    Всегда возвращаем список объектов:
    [
      { "code": "...", "title": "...", "url": "...", "description": "..." }
    ]
    """
    if DATA_PATH.exists():
        try:
            data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data  # корректный формат
        except Exception:
            pass

    # если файла нет или формат сломан → создаём пустой
    return []


def save_codes(codes: list):
    """
    Сохраняем список объектов
    """
    DATA_PATH.write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
