from jarvis.tools.base import PermissionTier, Tool


def build_remember_tool(memory_store):
    def _remember(key: str, value: str) -> str:
        memory_store.remember_note(key, value)
        return f"Remembered: {key} = {value}"

    return Tool(
        name="remember_note",
        description="Save a fact/note the user explicitly asks JARVIS to remember, under a short key.",
        tier=PermissionTier.ACTION,
        parameters={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Short label for the note, e.g. 'wifi_password'."},
                "value": {"type": "string", "description": "The information to remember."},
            },
            "required": ["key", "value"],
        },
        handler=_remember,
    )


def build_recall_tool(memory_store):
    def _recall() -> str:
        notes = memory_store.list_notes()
        if not notes:
            return "No notes saved yet."
        return "\n".join(f"{k}: {v}" for k, v in notes.items())

    return Tool(
        name="recall_notes",
        description="List everything currently saved in JARVIS's local memory.",
        tier=PermissionTier.READ,
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_recall,
    )


def build_forget_tool(memory_store):
    def _forget(key: str) -> str:
        existed = memory_store.forget_note(key)
        return f"Forgot '{key}'." if existed else f"No note called '{key}' was found."

    return Tool(
        name="forget_note",
        description="Delete a previously remembered note by its key.",
        tier=PermissionTier.ACTION,
        parameters={
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
        handler=_forget,
    )
