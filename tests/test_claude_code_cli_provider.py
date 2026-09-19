"""
jarvis/core/providers/claude_code_cli_provider.py tests. This provider
shells out to the locally-installed `claude` CLI's non-interactive print
mode instead of calling a metered API - these tests mock subprocess.run
entirely (no real CLI call), pinning: the safety flags are always passed,
every failure mode (missing binary, timeout, nonzero exit, malformed
output) returns a clear AIResponse instead of raising, JSON output is
parsed correctly, and history is formatted into the prompt the same way
the other providers do (never relying on the CLI's own --resume).
"""
import subprocess
from types import SimpleNamespace

import pytest

from jarvis.core.ai_core import build_provider
from jarvis.core.providers.claude_code_cli_provider import ClaudeCodeCliProvider


def _completed(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def _json_result(text, is_error=False):
    import json
    return json.dumps({"result": text, "is_error": is_error, "type": "result"})


@pytest.fixture(autouse=True)
def provider():
    return ClaudeCodeCliProvider(command="claude", timeout_seconds=10)


# ── routing (build_provider) ────────────────────────────────────────────────

def test_build_provider_routes_to_claude_code_cli():
    p = build_provider({
        "ai_provider": "claude_code_cli",
        "claude_code_cli_command": "my-claude",
        "claude_code_cli_timeout_seconds": 30,
    })
    assert isinstance(p, ClaudeCodeCliProvider)
    assert p._command == "my-claude"
    assert p._timeout == 30


def test_build_provider_uses_defaults_when_unspecified():
    p = build_provider({"ai_provider": "claude_code_cli"})
    assert p._command == "claude"
    assert p._timeout == 45


# ── _format_prompt (history handling - no reliance on CLI --resume) ────────

def test_format_prompt_single_message_is_sent_as_is():
    history = [{"role": "user", "content": "Hello"}]
    assert ClaudeCodeCliProvider._format_prompt(history) == "Hello"


def test_format_prompt_includes_prior_turns_for_multi_message_history():
    history = [
        {"role": "user", "content": "What's 2+2?"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "And plus 3?"},
    ]
    prompt = ClaudeCodeCliProvider._format_prompt(history)
    assert "User: What's 2+2?" in prompt
    assert "Assistant: 4" in prompt
    assert "User: And plus 3?" in prompt


def test_format_prompt_empty_history_is_empty_string():
    assert ClaudeCodeCliProvider._format_prompt([]) == ""


# ── send() happy path + safety flags ────────────────────────────────────────

def test_send_passes_safety_flags_and_returns_parsed_result(monkeypatch, provider):
    captured = {}

    def _fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _completed(stdout=_json_result("Hi there!"))

    monkeypatch.setattr(subprocess, "run", _fake_run)

    response = provider.send([{"role": "user", "content": "Hi"}], tool_schemas=[])

    assert response.text == "Hi there!"
    assert response.tool_calls == []
    assert response.needs_tool_execution is False
    assert "--restricted" in captured["args"]
    assert "--permission-prompts" in captured["args"]
    assert "none" in captured["args"]
    assert "--output-format" in captured["args"]
    assert "json" in captured["args"]
    assert captured["kwargs"]["timeout"] == 10


def test_send_tool_results_never_returns_tool_calls(monkeypatch, provider):
    """Contract completeness only - AICore never actually calls this since
    needs_tool_execution is always False for this provider."""
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: _completed(stdout=_json_result("ok")))

    response = provider.send_tool_results([{"role": "user", "content": "hi"}], None, [], [])

    assert response.tool_calls == []


def test_send_with_empty_history_does_not_call_subprocess(monkeypatch, provider):
    called = {"yes": False}
    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: called.__setitem__("yes", True))

    response = provider.send([], tool_schemas=[])

    assert called["yes"] is False
    assert "no message" in response.text.lower()


# ── error handling: never raises, always a clear AIResponse ────────────────

def test_missing_binary_is_reported_not_raised(monkeypatch, provider):
    def _boom(args, **kw):
        raise FileNotFoundError("no such file")
    monkeypatch.setattr(subprocess, "run", _boom)

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "not found on path" in response.text.lower()
    assert "claude" in response.text.lower()


def test_timeout_is_reported_not_raised(monkeypatch, provider):
    def _boom(args, **kw):
        raise subprocess.TimeoutExpired(cmd=args, timeout=10)
    monkeypatch.setattr(subprocess, "run", _boom)

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "timed out" in response.text.lower()


def test_unexpected_subprocess_exception_is_reported_not_raised(monkeypatch, provider):
    def _boom(args, **kw):
        raise OSError("permission denied")
    monkeypatch.setattr(subprocess, "run", _boom)

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "permission denied" in response.text.lower()


def test_nonzero_exit_code_is_reported_with_stderr(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run",
                        lambda args, **kw: _completed(stderr="something broke", returncode=1))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "exit 1" in response.text.lower()
    assert "something broke" in response.text


def test_rate_limit_error_gets_a_helpful_hint(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run",
                        lambda args, **kw: _completed(stderr="Error: usage limit reached", returncode=1))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "rate limit" in response.text.lower() or "usage cap" in response.text.lower()


def test_auth_error_gets_a_helpful_hint(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run",
                        lambda args, **kw: _completed(stderr="Error: not logged in", returncode=1))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "logged in" in response.text.lower() or "authenticate" in response.text.lower()


def test_is_error_true_in_json_payload_is_surfaced(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run",
                        lambda args, **kw: _completed(stdout=_json_result("bad request", is_error=True)))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "error" in response.text.lower()
    assert "bad request" in response.text


def test_malformed_json_output_falls_back_to_raw_stdout(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run",
                        lambda args, **kw: _completed(stdout="plain text reply, not json"))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert response.text == "plain text reply, not json"


def test_empty_stdout_is_reported_not_blank(monkeypatch, provider):
    monkeypatch.setattr(subprocess, "run", lambda args, **kw: _completed(stdout=""))

    response = provider.send([{"role": "user", "content": "hi"}], [])

    assert "empty response" in response.text.lower()
