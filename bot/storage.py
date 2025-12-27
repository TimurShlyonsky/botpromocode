import json
from pathlib import Path
from typing import List, Dict

DEFAULT_DATA_PATH = Path("data/promo_codes.json")


def load_codes(path: Path = DEFAULT_DATA_PATH) -> List[Dict]:
    """
    Загружаем сохранённые коды из указанного JSON-файла.

    Всегда возвращаем список объектов:
    [
      { "code": "...", "title": "...", "url": "...", "description": "..." }
    ]
    """
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass

    # если файла нет или формат сломан → возвращаем пустой список
    return []


def save_codes(codes: List[Dict], path: Path = DEFAULT_DATA_PATH) -> None:
    """
    Сохраняем список объектов в указанный JSON-файл.
    """
    # гарантируем, что директория data/ существует
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(codes, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
