import asyncio

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
    if provider_name == "anthropic":
        log.warning("ai_provider is 'anthropic' but no anthropic_api_key is set; falling back to echo mode.")
    return EchoProvider()


class AICore:
    def __init__(self, settings: dict, memory_store, tool_registry: ToolRegistry, permission_manager: PermissionManager):
        self.settings = settings
        self.memory = memory_store
        self.tools = tool_registry
        self.permissions = permission_manager
        self.provider = build_provider(settings)

    async def handle_message(self, user_text: str) -> str:
        self.memory.append_history("user", user_text)
        history = self.memory.get_history()
        tool_schemas = self.tools.anthropic_schemas()

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
            return f"User did not approve running '{tool_name}'."

        try:
            return await asyncio.to_thread(tool.run, **tool_args)
        except Exception as exc:  # tool failures shouldn't crash the assistant
            log.exception("Tool '%s' failed", tool_name)
            return f"Tool '{tool_name}' failed: {exc}"
