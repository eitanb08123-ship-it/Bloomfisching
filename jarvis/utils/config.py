import copy
import json
import shutil
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
EXAMPLE_PATH = CONFIG_DIR / "settings.example.json"


def _deep_merge(base: dict, override: dict) -> dict:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_settings() -> dict:
    with open(EXAMPLE_PATH, "r", encoding="utf-8") as f:
        defaults = json.load(f)

    if not SETTINGS_PATH.exists():
        shutil.copy(EXAMPLE_PATH, SETTINGS_PATH)
        return defaults

    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        user_settings = json.load(f)

    return _deep_merge(defaults, user_settings)


def save_settings(settings: dict) -> None:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
