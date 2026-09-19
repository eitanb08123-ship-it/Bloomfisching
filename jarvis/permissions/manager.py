from jarvis.utils.logger import get_logger

log = get_logger("permissions")


class PermissionManager:
    """
    Every tool call is authorized immediately - there is no confirmation step.
    The only safety net is undo_last_action ('חזור'/'undo'): JARVIS acts
    first, and the user can reverse the most recent reversible action after
    the fact. See each tool's own undo logic for what it can and can't
    actually restore. Nothing here bypasses Windows itself (UAC prompts,
    antivirus, file permissions, etc. still apply underneath whatever a
    tool does).
    """

    async def authorize(self, tool, args: dict) -> bool:
        return True
