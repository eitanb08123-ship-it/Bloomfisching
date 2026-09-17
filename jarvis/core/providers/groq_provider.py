import json

from groq import Groq

from jarvis.core.providers.base import AIProvider, AIResponse, ToolCallRequest

SYSTEM_PROMPT = (
    "You are JARVIS, a helpful local AI assistant running on the user's own Windows PC. "
    "You can converse normally, and you can call tools to check system status, search/read files, "
    "open or close applications, open websites, and manage a small local memory of notes. "
    "Only call a tool when the user's request actually needs it. Actions that change anything on the "
    "computer (opening/closing apps, opening websites, saving/forgetting notes) are shown to the user "
    "for confirmation before they run, so you can propose them freely and explain what you're about to do."
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
