from jarvis.tools.base import PermissionTier, Tool


def build_remember_tool(memory_store, undo_stack):
    def _remember(key: str, value: str) -> str:
        previous = memory_store.list_notes().get(key)

        def _undo() -> str:
            if previous is None:
                memory_store.forget_note(key)
                return f"Undid: removed note '{key}'."
            memory_store.remember_note(key, previous)
            return f"Undid: restored note '{key}' to its previous value."

        memory_store.remember_note(key, value)
        undo_stack.push("remember_note", f"undo remembering '{key}'", _undo)
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


def build_forget_tool(memory_store, undo_stack):
    def _forget(key: str) -> str:
        previous = memory_store.list_notes().get(key)
        existed = memory_store.forget_note(key)

        if existed:
            def _undo() -> str:
                memory_store.remember_note(key, previous)
                return f"Undid: restored note '{key}'."

            undo_stack.push("forget_note", f"undo forgetting '{key}'", _undo)
            return f"Forgot '{key}'."
        return f"No note called '{key}' was found."

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
