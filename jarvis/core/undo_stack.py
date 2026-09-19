from dataclasses import dataclass
from typing import Callable

from jarvis.utils.logger import get_logger

log = get_logger("undo")


@dataclass
class UndoEntry:
    tool_name: str
    description: str
    undo_fn: Callable[[], str]


class UndoStack:
    """Tracks reversible actions so 'undo'/'חזור' can walk them back one at a
    time. Only actions that registered an undo_fn end up here - not every
    action can be reversed (see each tool's own undo logic for what it
    actually restores)."""

    def __init__(self):
        self._entries: list[UndoEntry] = []

    def push(self, tool_name: str, description: str, undo_fn: Callable[[], str]) -> None:
        self._entries.append(UndoEntry(tool_name, description, undo_fn))

    def undo_last(self) -> str:
        if not self._entries:
            return "Nothing to undo."
        entry = self._entries.pop()
        try:
            outcome = entry.undo_fn()
        except Exception as exc:
            log.exception("Undo failed for %s", entry.tool_name)
            return f"Tried to undo '{entry.tool_name}' ({entry.description}) but it failed: {exc}"
        return outcome
