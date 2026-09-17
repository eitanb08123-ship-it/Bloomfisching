import asyncio

from jarvis.core import commands
from jarvis.core.providers.echo_provider import EchoProvider
from jarvis.permissions.manager import PermissionManager
from jarvis.tools.registry import ToolRegistry
from jarvis.utils.logger import get_logger

log = get_logger("ai_core")

MAX_TOOL_ROUNDS = 5


def build_provider(settings: dict):
    provider_name = settings.get("ai_provider", "echo")

    if provider_name == "anthropic" and settings.get("anthropic_api_key"):
        from jarvis.core.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings["anthropic_api_key"], settings["anthropic_model"])

    if provider_name == "groq" and settings.get("groq_api_key"):
        from jarvis.core.providers.groq_provider import GroqProvider

        return GroqProvider(settings["groq_api_key"], settings["groq_model"])

    if provider_name in ("anthropic", "groq"):
        log.warning("ai_provider is '%s' but no matching API key is set; falling back to echo mode.", provider_name)
    return EchoProvider()


class AICore:
    def __init__(
        self,
        settings: dict,
        memory_store,
        tool_registry: ToolRegistry,
        permission_manager: PermissionManager,
        on_activity=None,
    ):
        self.settings = settings
        self.memory = memory_store
        self.tools = tool_registry
        self.permissions = permission_manager
        self.provider = build_provider(settings)
        # on_activity(tool_name, args, result) -> awaited; lets the server push
        # a live "what JARVIS just did" feed to the UI, separate from the
        # chat reply text.
        self.on_activity = on_activity

    async def handle_message(self, user_text: str) -> str:
        command = commands.match_command(user_text)
        if command:
            reply = self._handle_command(command)
            self.memory.append_history("user", user_text)
            self.memory.append_history("assistant", reply)
            return reply

        self.memory.append_history("user", user_text)
        history = self.memory.get_history()
        tool_schemas = (
            self.tools.anthropic_schemas() if self.provider.schema_format == "anthropic" else self.tools.openai_schemas()
        )

        response = await asyncio.to_thread(self.provider.send, history, tool_schemas)

        rounds = 0
        while response.needs_tool_execution and rounds < MAX_TOOL_ROUNDS:
            rounds += 1
            tool_results = []
            for call in response.tool_calls:
                output = await self._execute_tool_call(call.tool_name, call.tool_args)
                tool_results.append({"call_id": call.call_id, "tool_name": call.tool_name, "output": output})

            response = await asyncio.to_thread(
                self.provider.send_tool_results, history, response, tool_results, tool_schemas
            )

        final_text = response.text or "(no response)"
        self.memory.append_history("assistant", final_text)
        return final_text

    async def _execute_tool_call(self, tool_name: str, tool_args: dict) -> str:
        tool = self.tools.get(tool_name)
        if tool is None:
            log.warning("Model requested unknown tool: %s", tool_name)
            return f"Unknown tool: {tool_name}"

        approved = await self.permissions.authorize(tool, tool_args)
        if not approved:
            result = f"User did not approve running '{tool_name}'."
            await self._report_activity(tool_name, tool_args, result)
            return result

        try:
            result = await asyncio.to_thread(tool.run, **tool_args)
        except Exception as exc:  # tool failures shouldn't crash the assistant
            log.exception("Tool '%s' failed", tool_name)
            result = f"Tool '{tool_name}' failed: {exc}"

        await self._report_activity(tool_name, tool_args, result)
        return result

    async def _report_activity(self, tool_name: str, tool_args: dict, result: str) -> None:
        if self.on_activity:
            await self.on_activity(tool_name, tool_args, result)

    def _handle_command(self, command: str) -> str:
        if command == "serious_off":
            self.permissions.autonomous = False
            return "Serious mode off — I'll ask for confirmation again before running actions."
        if command == "serious_on":
            self.permissions.autonomous = True
            return (
                "Serious mode on — I'll act immediately without asking, for anything you ask me to do. "
                "Say 'חזור' or 'undo' any time to reverse my last action."
            )
        if command == "voice_off":
            self.settings["voice"]["enabled"] = False
            return "Voice replies turned off."
        if command == "voice_on":
            self.settings["voice"]["enabled"] = True
            return "Voice replies turned on — I'll speak my replies out loud from now on."
        return "(unrecognized command)"
