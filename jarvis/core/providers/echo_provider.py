import re

from jarvis.core.providers.base import AIProvider, AIResponse, ToolCallRequest

HELP_TEXT = (
    "I'm running in offline/basic mode (no AI provider configured in config/settings.json).\n"
    "I can still run simple commands, e.g.:\n"
    "  system info | search <text> | google <query> | read file <path> | open <app or url> | "
    "close <process> | remember <key> = <value> | recall | forget <key> | undo\n"
    "Add an Anthropic API key to config/settings.json and set \"ai_provider\": \"anthropic\" "
    "for full natural-language understanding."
)

_PATTERNS = [
    (re.compile(r"^(system info|מידע מערכת|cpu|מעבד)", re.I), "get_system_info", lambda m, rest: {}),
    (re.compile(r"^(google|search web|חפש בגוגל|חפש באינטרנט)\s+(.+)", re.I), "web_search", lambda m, rest: {"query": m.group(2)}),
    (re.compile(r"^(search|חפש)\s+(.+)", re.I), "search_files", lambda m, rest: {"query": m.group(2)}),
    (re.compile(r"^(read file|קרא קובץ)\s+(.+)", re.I), "read_file", lambda m, rest: {"path": m.group(2)}),
    (re.compile(r"^(open website|open url|פתח אתר)\s+(.+)", re.I), "open_website", lambda m, rest: {"url": m.group(2)}),
    (re.compile(r"^(open|פתח)\s+(.+)", re.I), "open_application", lambda m, rest: {"target": m.group(2)}),
    (re.compile(r"^(close|סגור)\s+(.+)", re.I), "close_application", lambda m, rest: {"process_name": m.group(2)}),
    (re.compile(r"^(remember|זכור)\s+(.+?)\s*=\s*(.+)", re.I), "remember_note", lambda m, rest: {"key": m.group(2), "value": m.group(3)}),
    (re.compile(r"^(recall|מה זכור)", re.I), "recall_notes", lambda m, rest: {}),
    (re.compile(r"^(forget|תשכח)\s+(.+)", re.I), "forget_note", lambda m, rest: {"key": m.group(2)}),
    (re.compile(r"^(undo|חזור|בטל)", re.I), "undo_last_action", lambda m, rest: {}),
]


class EchoProvider(AIProvider):
    """No external API calls. Parses simple commands so the whole tool +
    permission pipeline can be tried out with zero setup."""

    def send(self, history: list[dict], tool_schemas: list[dict]) -> AIResponse:
        last_user = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
        for pattern, tool_name, build_args in _PATTERNS:
            match = pattern.match(last_user.strip())
            if match:
                args = build_args(match, last_user)
                return AIResponse(tool_calls=[ToolCallRequest(tool_name, args, call_id="echo-1")])
        return AIResponse(text=HELP_TEXT)

    def send_tool_results(self, history, prior_response, tool_results: list[dict], tool_schemas) -> AIResponse:
        parts = [f"[{r['tool_name']}] {r['output']}" for r in tool_results]
        return AIResponse(text="\n".join(parts))
