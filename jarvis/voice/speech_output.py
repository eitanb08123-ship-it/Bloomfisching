import platform

from jarvis.utils.logger import get_logger

log = get_logger("voice.output")

try:
    import pyttsx3

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

_IS_WINDOWS = platform.system() == "Windows"


def is_available() -> bool:
    return _AVAILABLE


def speak(text: str, rate: int = 175) -> None:
    """Runs on a worker thread (via asyncio.to_thread). On Windows, pyttsx3's
    SAPI5 backend needs COM initialized on whatever thread actually uses it,
    and a cached engine object isn't safe to reuse across different worker
    threads - so this creates a fresh engine and initializes COM fresh on
    every call, entirely within this one thread. Without this, calls
    silently fail (or raise 'CoInitialize has not been called') depending on
    which thread pool worker asyncio happens to pick."""
    if not _AVAILABLE:
        log.warning("pyttsx3 not installed; skipping speech output.")
        return

    com_initialized = False
    if _IS_WINDOWS:
        try:
            import pythoncom

            pythoncom.CoInitialize()
            com_initialized = True
        except ImportError:
            pass  # pywin32 missing; pyttsx3 will most likely fail below too

    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", rate)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    finally:
        if com_initialized:
            import pythoncom

            pythoncom.CoUninitialize()
