from jarvis.utils.logger import get_logger

log = get_logger("voice.output")

try:
    import pyttsx3

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_engine = None


def is_available() -> bool:
    return _AVAILABLE


def _get_engine(rate: int):
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", rate)
    return _engine


def speak(text: str, rate: int = 175) -> None:
    if not _AVAILABLE:
        log.warning("pyttsx3 not installed; skipping speech output.")
        return
    engine = _get_engine(rate)
    engine.say(text)
    engine.runAndWait()
