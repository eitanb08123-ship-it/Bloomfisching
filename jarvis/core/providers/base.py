from abc import ABC, abstractmethod


class ToolCallRequest:
    def __init__(self, tool_name: str, tool_args: dict, call_id: str):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.call_id = call_id


class AIResponse:
    """Either a final text reply, or a list of tool calls the core must run
    and feed back before the provider can produce a final reply."""

    def __init__(self, text: str | None = None, tool_calls: list[ToolCallRequest] | None = None, raw=None):
        self.text = text
        self.tool_calls = tool_calls or []
        self.raw = raw

    @property
    def needs_tool_execution(self) -> bool:
        return bool(self.tool_calls)


class AIProvider(ABC):
    @abstractmethod
    def send(self, history: list[dict], tool_schemas: list[dict]) -> AIResponse:
        """Send the conversation so far (+ available tools) and get a response."""

    @abstractmethod
    def send_tool_results(self, history: list[dict], prior_response, tool_results: list[dict], tool_schemas: list[dict]) -> AIResponse:
        """Continue the conversation after tool(s) ran, using their results."""
