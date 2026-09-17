"""Deterministic phrase-triggered commands, handled before the AI provider
ever sees the message - so they work the same in Echo/Anthropic/Groq mode
and don't depend on the model understanding anything. Order matters: an
"off" phrase is checked before the matching "on" phrase because e.g.
'בטל מצב רציני' contains 'מצב רציני' as a substring."""

_SERIOUS_OFF = ("בטל מצב רציני", "מצב רגיל", "normal mode", "disable serious mode")
_SERIOUS_ON = ("מצב רציני", "serious mode")
_VOICE_OFF = ("תכבה קול", "כבה קול", "disable voice", "voice off")
_VOICE_ON = ("תדליק קול", "הפעל קול", "enable voice", "voice on")


def match_command(text: str) -> str | None:
    normalized = text.strip().lower()
    if any(phrase in normalized for phrase in _SERIOUS_OFF):
        return "serious_off"
    if any(phrase in normalized for phrase in _SERIOUS_ON):
        return "serious_on"
    if any(phrase in normalized for phrase in _VOICE_OFF):
        return "voice_off"
    if any(phrase in normalized for phrase in _VOICE_ON):
        return "voice_on"
    return None
