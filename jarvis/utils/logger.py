import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

_configured = False


def get_logger(name: str) -> logging.Logger:
    global _configured
    root = logging.getLogger("jarvis")
    if not _configured:
        root.setLevel(logging.INFO)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "jarvis.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        console_handler = logging.StreamHandler()
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(fmt)
        console_handler.setFormatter(fmt)
        root.addHandler(file_handler)
        root.addHandler(console_handler)
        _configured = True
    return logging.getLogger(f"jarvis.{name}")
