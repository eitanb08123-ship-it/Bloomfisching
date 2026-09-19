import json
import subprocess
import time

from jarvis.core.providers.base import AIProvider, AIResponse
from jarvis.utils.logger import get_logger

log = get_logger("providers.claude_code_cli")

DEFAULT_TIMEOUT_SECONDS = 45


class ClaudeCodeCliProvider(AIProvider):
    """Routes JARVIS's conversation through the locally-installed Claude
    Code CLI's non-interactive print mode (`claude -p`), instead of a
    metered Anthropic API key. If the CLI is authenticated to a Claude
    Pro/Max subscription login (not an ANTHROPIC_API_KEY env var), usage
    is covered by that subscription rather than billed per token - it's
    on the user to have logged in that way; this provider has no way to
    check which auth method the CLI is actually using.

    TEXT-ONLY: unlike AnthropicProvider/GroqProvider, this NEVER returns
    tool_calls. The CLI has its own built-in tools (bash, file edit, ...),
    unrelated to jarvis/tools/*, and there is no reliable way to make an
    external CLI subprocess populate THIS app's tool_calls contract - so
    every response here is final text, and JARVIS's own tools
    (open_application, web_search, memory, ...) are unavailable while
    this provider is selected. Documented, not silently degraded.

    SAFETY: every call passes --restricted (removes the CLI's own
    bash/file-editing/code-execution tools entirely) and
    --permission-prompts none (anything that would still need a prompt is
    auto-denied instead of hanging with no TTY to answer it). This
    integration should only ever produce a text reply, never let an
    embedded CLI session take independent action on the user's machine.

    HISTORY: the CLI does support its own session persistence
    (--session-id/--resume), but using it would create a second,
    independent copy of conversation state that could drift from
    JARVIS's own memory_store.json (e.g. after the user clears history).
    Instead, this formats the existing `history` list into the prompt
    text on every call - exactly like AnthropicProvider/GroqProvider do -
    keeping ONE source of truth, at the cost of resending prior turns as
    text each time rather than leaning on the CLI's own compaction.
    """

    schema_format = "anthropic"  # unused - this provider ignores tool_schemas entirely

    def __init__(self, command: str = "claude", timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS):
        self._command = command
        self._timeout = timeout_seconds

    @staticmethod
    def _format_prompt(history: list[dict]) -> str:
        if not history:
            return ""
        if len(history) == 1:
            return history[0]["content"]
        lines = []
        for msg in history[:-1]:
            speaker = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{speaker}: {msg['content']}")
        lines.append(f"User: {history[-1]['content']}")
        return (
            "Continue this conversation naturally - reply only with your next "
            "message, no preamble.\n\n" + "\n".join(lines)
        )

    def send(self, history: list[dict], tool_schemas: list[dict]) -> AIResponse:
        return self._run(self._format_prompt(history))

    def send_tool_results(self, history, prior_response, tool_results, tool_schemas) -> AIResponse:
        # Never actually reached in practice: needs_tool_execution is always
        # False for this provider (tool_calls is always []), so AICore's
        # tool-execution loop never calls this. Implemented only so the
        # AIProvider contract is fully satisfied.
        return self._run(self._format_prompt(history))

    def _run(self, prompt: str) -> AIResponse:
        if not prompt.strip():
            return AIResponse(text="(no message to send)")

        args = [
            self._command, "-p", prompt,
            "--restricted",
            "--permission-prompts", "none",
            "--output-format", "json",
        ]

        started = time.monotonic()
        try:
            proc = subprocess.run(
                args, capture_output=True, text=True, timeout=self._timeout,
                encoding="utf-8", errors="replace",
            )
        except FileNotFoundError:
            log.error("'%s' was not found on PATH.", self._command)
            return AIResponse(text=(
                f"Claude Code CLI provider error: '{self._command}' was not found on PATH. "
                f"Install it (npm install -g @anthropic-ai/claude-code) or set "
                f'"claude_code_cli_command" in settings.json to its full path.'
            ))
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - started
            log.error("timed out after %.1fs.", elapsed)
            return AIResponse(text=(
                f"Claude Code CLI provider error: the call timed out after {self._timeout:.0f}s "
                f'with no response. Try again, or raise "claude_code_cli_timeout_seconds" in settings.json.'
            ))
        except Exception as exc:
            log.exception("subprocess failed unexpectedly.")
            return AIResponse(text=f"Claude Code CLI provider error: {exc}")

        elapsed = time.monotonic() - started

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            log.error("exited %s after %.1fs: %s", proc.returncode, elapsed, stderr[:500])
            hint = ""
            lowered = stderr.lower()
            if "rate limit" in lowered or "quota" in lowered or "usage limit" in lowered:
                hint = " (looks like a rate limit/usage cap on your Claude subscription - wait and retry.)"
            elif "not logged in" in lowered or "authentic" in lowered or "login" in lowered:
                hint = " (the CLI may not be logged in - run 'claude' interactively once to authenticate.)"
            return AIResponse(text=(
                f"Claude Code CLI provider error (exit {proc.returncode}) after {elapsed:.1f}s: "
                f"{stderr or '(no error output)'}{hint}"
            ))

        text = self._extract_text(proc.stdout)
        log.info("reply in %.1fs (%d chars).", elapsed, len(text))
        return AIResponse(text=text, raw=proc.stdout)

    @staticmethod
    def _extract_text(stdout: str) -> str:
        stdout = (stdout or "").strip()
        if not stdout:
            return "(empty response from claude_code_cli)"
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return stdout  # not JSON (e.g. a plain-text fallback) - use as-is

        if payload.get("is_error"):
            return f"Claude Code CLI reported an error: {payload.get('result') or payload}"
        return payload.get("result", stdout)
