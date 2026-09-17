import json
from pathlib import Path
from threading import Lock

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_PATH = DATA_DIR / "memory.json"

_lock = Lock()


class MemoryStore:
    """
    Local, file-based memory. Two parts:
      - history: recent conversation turns (bounded, for AI context)
      - notes: user-managed facts the user explicitly asked JARVIS to remember

    Everything lives in data/memory.json, in plain readable JSON, so the user
    can open, edit, or wipe it by hand at any time.
    """

    def __init__(self, max_history_messages: int = 40):
        self.max_history_messages = max_history_messages
        self._data = self._load()

    def _load(self) -> dict:
        if MEMORY_PATH.exists():
            try:
                with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {"history": [], "notes": {}}

    def _save(self) -> None:
        with _lock:
            with open(MEMORY_PATH, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_history(self) -> list[dict]:
        return list(self._data["history"])

    def append_history(self, role: str, content: str) -> None:
        self._data["history"].append({"role": role, "content": content})
        overflow = len(self._data["history"]) - self.max_history_messages
        if overflow > 0:
            self._data["history"] = self._data["history"][overflow:]
        self._save()

    def clear_history(self) -> None:
        self._data["history"] = []
        self._save()

    def remember_note(self, key: str, value: str) -> None:
        self._data["notes"][key] = value
        self._save()

    def forget_note(self, key: str) -> bool:
        existed = key in self._data["notes"]
        self._data["notes"].pop(key, None)
        self._save()
        return existed

    def list_notes(self) -> dict:
        return dict(self._data["notes"])
