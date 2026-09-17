import asyncio
import uuid

from jarvis.tools.base import PermissionTier
from jarvis.utils.logger import get_logger

log = get_logger("permissions")


class PermissionDenied(Exception):
    pass


class PermissionManager:
    """
    Gatekeeper between the AI core and the tools.

    READ tools run immediately. ACTION and CRITICAL tools are described to the
    user first ("planned action") and only run after the UI sends back an
    explicit approval. CRITICAL tools require a second, distinct confirmation.
    Nothing here ever bypasses Windows itself (UAC prompts, antivirus, file
    permissions, etc. still apply underneath whatever a tool does).
    """

    def __init__(self, request_confirmation, autonomous: bool = False):
        # request_confirmation(request_id, tool, args, tier, stage) -> awaited,
        # resolved externally (by the server) when the user answers.
        self._request_confirmation = request_confirmation
        self._pending: dict[str, asyncio.Future] = {}
        # Autonomous mode: run everything immediately, no confirmations at all,
        # relying on each tool's undo support (see undo_last_action) as the
        # safety net instead. Some actions (e.g. closing an app, opening a
        # website) can't be fully undone - see their own tool descriptions.
        self.autonomous = autonomous

    def resolve(self, request_id: str, approved: bool) -> None:
        future = self._pending.pop(request_id, None)
        if future and not future.done():
            future.set_result(approved)

    async def authorize(self, tool, args: dict) -> bool:
        if self.autonomous or tool.tier == PermissionTier.READ:
            return True

        if not await self._ask(tool, args, stage=1):
            log.info("User denied action: %s(%s)", tool.name, args)
            return False

        if tool.tier == PermissionTier.CRITICAL:
            if not await self._ask(tool, args, stage=2):
                log.info("User denied critical confirmation: %s(%s)", tool.name, args)
                return False

        return True

    async def _ask(self, tool, args: dict, stage: int) -> bool:
        request_id = str(uuid.uuid4())
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future
        await self._request_confirmation(request_id, tool, args, stage)
        try:
            return await asyncio.wait_for(future, timeout=120)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            log.warning("Confirmation timed out for %s", tool.name)
            return False
