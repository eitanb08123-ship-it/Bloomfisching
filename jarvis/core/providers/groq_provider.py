import json

from groq import Groq

from jarvis.core.providers.base import AIProvider, AIResponse, ToolCallRequest

SYSTEM_PROMPT = (
    "You are JARVIS, a helpful local AI assistant running on the user's own Windows PC. "
    "You can converse normally, and you can call tools to check system status, search/read files, "
    "search the web, open or close applications, open websites, and manage a small local memory of notes. "
    "Only call a tool when the user's request actually needs it. Every tool call runs immediately with "
    "no confirmation step, so when a request is ambiguous, don't stop to ask a clarifying question first "
    "- pick your best interpretation and act on it right away. If you got it wrong, the user can say "
    "'חזור'/'undo' to reverse your last action, so acting fast beats pausing to ask. "
    "If the user asks for something no existing tool covers, say so plainly and explain what tool or "
    "capability would be needed, rather than guessing at unsupported actions."
)


class GroqProvider(AIProvider):
    """Uses Groq's OpenAI-compatible chat completions API with function calling."""

    schema_format = "openai"

    def __init__(self, api_key: str, model: str):
        self._client = Groq(api_key=api_key)
        self._model = model

    @staticmethod
    def _to_messages(history: list[dict]) -> list[dict]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend({"role": m["role"], "content": m["content"]} for m in history)
        return messages

    def send(self, history: list[dict], tool_schemas: list[dict]) -> AIResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=self._to_messages(history),
            tools=tool_schemas or None,
            max_tokens=1024,
        )
        return self._parse(response)

    def send_tool_results(self, history, prior_response: AIResponse, tool_results: list[dict], tool_schemas) -> AIResponse:
        messages = self._to_messages(history)
        messages.append(self._assistant_message(prior_response))
        for result in tool_results:
            messages.append({"role": "tool", "tool_call_id": result["call_id"], "content": result["output"]})

        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tool_schemas or None,
            max_tokens=1024,
        )
        return self._parse(response)

    @staticmethod
    def _assistant_message(prior_response: AIResponse) -> dict:
        message = {"role": "assistant", "content": prior_response.text}
        if prior_response.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.call_id,
                    "type": "function",
                    "function": {"name": call.tool_name, "arguments": json.dumps(call.tool_args)},
                }
                for call in prior_response.tool_calls
            ]
        return message

    @staticmethod
    def _parse(response) -> AIResponse:
        message = response.choices[0].message
        tool_calls = []
        for call in message.tool_calls or []:
            args = json.loads(call.function.arguments or "{}")
            tool_calls.append(ToolCallRequest(call.function.name, args, call.id))
        return AIResponse(text=message.content, tool_calls=tool_calls, raw=message)
