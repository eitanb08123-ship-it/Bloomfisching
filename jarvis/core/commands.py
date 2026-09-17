"""Deterministic phrase-triggered commands, handled before the AI provider
ever sees the message - so they work the same in Echo/Anthropic/Groq mode
and don't depend on the model understanding anything."""

_VOICE_OFF = ("תכבה קול", "כבה קול", "disable voice", "voice off")
_VOICE_ON = ("תדליק קול", "הפעל קול", "enable voice", "voice on")


def match_command(text: str) -> str | None:
    normalized = text.strip().lower()
    if any(phrase in normalized for phrase in _VOICE_OFF):
        return "voice_off"
    if any(phrase in normalized for phrase in _VOICE_ON):
        return "voice_on"
    return None
