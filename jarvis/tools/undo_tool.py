from jarvis.tools.base import PermissionTier, Tool


def build_tool(undo_stack):
    return Tool(
        name="undo_last_action",
        description=(
            "Undo/revert the most recent state-changing action JARVIS performed, if it can be "
            "reversed. Call this whenever the user asks to undo, revert, go back, or says 'חזור'."
        ),
        tier=PermissionTier.READ,
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: undo_stack.undo_last(),
    )
