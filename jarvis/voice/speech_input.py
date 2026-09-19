from jarvis.utils.logger import get_logger

log = get_logger("voice.input")

try:
    import speech_recognition as sr

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def is_available() -> bool:
    return _AVAILABLE


def listen_once(language: str = "en-US", timeout: float = 6.0) -> str:
    """Capture one utterance from the default microphone and transcribe it.
    Raises RuntimeError if the speech_recognition/pyaudio stack isn't installed,
    or if no speech was captured/understood."""
    if not _AVAILABLE:
        raise RuntimeError(
            "Voice input requires the 'SpeechRecognition' and 'PyAudio' packages. "
            "Install them (see README) and enable voice in config/settings.json."
        )

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        try:
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=15)
        except sr.WaitTimeoutError as exc:
            raise RuntimeError("No speech detected.") from exc

    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError as exc:
        raise RuntimeError("Could not understand the audio.") from exc
    except sr.RequestError as exc:
        raise RuntimeError(f"Speech recognition service error: {exc}") from exc
