import anthropic

from jarvis.core.providers.base import AIProvider, AIResponse, ToolCallRequest

SYSTEM_PROMPT = (
    "You are JARVIS, a helpful local AI assistant running on the user's own Windows PC. "
    "You can converse normally, and you can call tools to check system status, search/read files, "
    "search the web, open or close applications, open websites, and manage a small local memory of notes. "
    "Only call a tool when the user's request actually needs it. Every tool call runs immediately with "
    "no confirmation step, so when a request is ambiguous, don't stop to ask a clarifying question first "
    "- pick your best interpretation and act on it right away. If you got it wrong, the user can say "
    "'חזור'/'undo' to reverse your last action, so acting fast beats pausing to ask."
)


class AnthropicProvider(AIProvider):
    schema_format = "anthropic"

    def __init__(self, api_key: str, model: str):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_messages(history: list[dict]) -> list[dict]:
        return [{"role": m["role"], "content": m["content"]} for m in history]

    def send(self, history: list[dict], tool_schemas: list[dict]) -> AIResponse:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self._to_messages(history),
            tools=tool_schemas,
        )
        return self._parse(response)

    def send_tool_results(self, history, prior_response, tool_results: list[dict], tool_schemas) -> AIResponse:
        messages = self._to_messages(history)
        messages.append({"role": "assistant", "content": prior_response.raw.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": r["call_id"], "content": r["output"]}
                    for r in tool_results
                ],
            }
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=messages,
            tools=tool_schemas,
        )
        return self._parse(response)

    @staticmethod
    def _parse(response) -> AIResponse:
        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCallRequest(block.name, block.input, block.id))
        return AIResponse(text="\n".join(text_parts) or None, tool_calls=tool_calls, raw=response)
