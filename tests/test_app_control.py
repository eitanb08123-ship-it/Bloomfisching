"""
jarvis/tools/app_control.py tests - ported from mark-liv's actions/open_app.py
fixes (changelog item #4): _open_visibly_via_start_menu() used raw
pyautogui.typewrite() (breaks under a non-English keyboard layout, since
typewrite() sends key events for whatever the ACTIVE LAYOUT maps a physical
key to) and claimed "Launched" the instant the keystroke sequence itself
didn't raise, with no check that anything actually opened. These tests pin:
clipboard-paste is used instead of raw typing when pyperclip is available
(with a graceful fallback when it isn't), and a launch is only reported as
successful once a matching process is actually observed.
"""
from types import SimpleNamespace

import pytest

from jarvis.core.undo_stack import UndoStack
from jarvis.tools import app_control as ac


class _FakePyperclip:
    def __init__(self, paste_value=""):
        self._clip = paste_value
        self.copied = []

    def copy(self, text):
        self.copied.append(text)
        self._clip = text

    def paste(self):
        return self._clip


class _FakePyautogui:
    def __init__(self):
        self.calls = []

    def press(self, key):
        self.calls.append(("press", key))

    def hotkey(self, *keys):
        self.calls.append(("hotkey", keys))

    def typewrite(self, text, interval=0.0):
        self.calls.append(("typewrite", text))


def _fake_process(name):
    return SimpleNamespace(info={"name": name})


@pytest.fixture(autouse=True)
def _no_real_sleeping(monkeypatch):
    monkeypatch.setattr(ac.time, "sleep", lambda s: None)


# ── _wait_for_clipboard ──────────────────────────────────────────────────────

def test_wait_for_clipboard_true_when_it_already_matches(monkeypatch):
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", True)
    monkeypatch.setattr(ac, "pyperclip", _FakePyperclip(paste_value="WhatsApp"))

    assert ac._wait_for_clipboard("WhatsApp") is True


def test_wait_for_clipboard_false_on_timeout(monkeypatch):
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", True)
    monkeypatch.setattr(ac, "pyperclip", _FakePyperclip(paste_value="something else"))

    assert ac._wait_for_clipboard("WhatsApp", timeout=0.01, poll=0.001) is False


def test_wait_for_clipboard_false_when_pyperclip_unavailable(monkeypatch):
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", False)

    assert ac._wait_for_clipboard("WhatsApp") is False


# ── _type_app_name (item 4: clipboard-paste, not raw keystrokes) ────────────

def test_type_app_name_uses_clipboard_paste_when_available(monkeypatch):
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", True)
    fake_clip = _FakePyperclip(paste_value="WhatsApp")
    monkeypatch.setattr(ac, "pyperclip", fake_clip)
    fake_gui = _FakePyautogui()
    monkeypatch.setattr(ac, "pyautogui", fake_gui, raising=False)

    ac._type_app_name("WhatsApp")

    assert fake_clip.copied == ["WhatsApp"]
    assert ("hotkey", ("ctrl", "v")) in fake_gui.calls
    assert not any(call[0] == "typewrite" for call in fake_gui.calls)


def test_type_app_name_falls_back_to_typewrite_without_pyperclip(monkeypatch):
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", False)
    fake_gui = _FakePyautogui()
    monkeypatch.setattr(ac, "pyautogui", fake_gui, raising=False)

    ac._type_app_name("WhatsApp")

    assert ("typewrite", "WhatsApp") in fake_gui.calls


def test_type_app_name_proceeds_even_if_clipboard_never_confirms(monkeypatch):
    """A clipboard race (real, observed in mark-liv: Qt fighting pyperclip
    for clipboard ownership) must not hang or raise - it still pastes."""
    monkeypatch.setattr(ac, "_PYPERCLIP_AVAILABLE", True)
    fake_clip = _FakePyperclip(paste_value="stale content")
    monkeypatch.setattr(ac, "pyperclip", fake_clip)
    fake_gui = _FakePyautogui()
    monkeypatch.setattr(ac, "pyautogui", fake_gui, raising=False)
    monkeypatch.setattr(ac, "_wait_for_clipboard", lambda text: False)

    ac._type_app_name("WhatsApp")

    assert ("hotkey", ("ctrl", "v")) in fake_gui.calls


# ── _is_process_running (item 4: verify before claiming success) ───────────

def test_is_process_running_true_when_a_matching_process_exists(monkeypatch):
    monkeypatch.setattr(ac.psutil, "process_iter",
                        lambda attrs=None: [_fake_process("WhatsApp.exe"), _fake_process("chrome.exe")])

    assert ac._is_process_running("whatsapp", timeout=0.01, poll=0.001) is True


def test_is_process_running_false_when_nothing_matches(monkeypatch):
    monkeypatch.setattr(ac.psutil, "process_iter",
                        lambda attrs=None: [_fake_process("chrome.exe")])

    assert ac._is_process_running("whatsapp", timeout=0.01, poll=0.001) is False


def test_is_process_running_true_for_empty_name():
    assert ac._is_process_running("") is True


def test_is_process_running_ignores_processes_it_cannot_read(monkeypatch):
    class _Broken:
        info = property(lambda self: (_ for _ in ()).throw(ac.psutil.NoSuchProcess(1)))

    monkeypatch.setattr(ac.psutil, "process_iter",
                        lambda attrs=None: [_Broken(), _fake_process("WhatsApp.exe")])

    assert ac._is_process_running("whatsapp", timeout=0.01, poll=0.001) is True


# ── _open_visibly_via_start_menu (item 4: don't claim success blindly) ──────

def test_start_menu_launch_reports_success_only_once_verified(monkeypatch):
    monkeypatch.setattr(ac, "pyautogui", _FakePyautogui(), raising=False)
    monkeypatch.setattr(ac, "_type_app_name", lambda app_name: None)
    monkeypatch.setattr(ac, "_is_process_running", lambda app_name, **kw: True)

    result = ac._open_visibly_via_start_menu("WhatsApp")

    assert result.startswith("Launched:")


def test_start_menu_launch_reports_honest_failure_when_unverified(monkeypatch):
    """The exact bug this fixes: previously this returned 'Launched' the
    instant the keystroke sequence didn't raise, even if nothing opened."""
    monkeypatch.setattr(ac, "pyautogui", _FakePyautogui(), raising=False)
    monkeypatch.setattr(ac, "_type_app_name", lambda app_name: None)
    monkeypatch.setattr(ac, "_is_process_running", lambda app_name, **kw: False)

    result = ac._open_visibly_via_start_menu("WhatsApp")

    assert not result.startswith("Launched:")
    assert "could not confirm" in result.lower()


def test_start_menu_launch_falls_back_to_instant_on_exception(monkeypatch):
    def _boom(key):
        raise RuntimeError("no display")
    monkeypatch.setattr(ac, "pyautogui", SimpleNamespace(press=_boom), raising=False)
    monkeypatch.setattr(ac, "_open_application_instant", lambda target: f"Launched: {target}")

    result = ac._open_visibly_via_start_menu("WhatsApp")

    assert result == "Launched: WhatsApp"


# ── build_open_tool: no bogus undo entry on an unverified launch ───────────

def test_open_tool_pushes_undo_only_on_a_verified_launch(monkeypatch):
    monkeypatch.setattr(ac, "_PYAUTOGUI_AVAILABLE", True)
    monkeypatch.setattr(ac.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ac, "_looks_like_path", lambda target: False)
    monkeypatch.setattr(ac, "_open_visibly_via_start_menu",
                        lambda app_name: "Could not confirm that WhatsApp launched via the Start menu - it may still be loading, or it might not be installed.")

    undo_stack = UndoStack()
    tool = ac.build_open_tool(undo_stack)

    result = tool.run(target="WhatsApp")

    assert "could not confirm" in result.lower()
    assert undo_stack.undo_last() == "Nothing to undo."


def test_open_tool_pushes_undo_on_a_verified_launch(monkeypatch):
    monkeypatch.setattr(ac, "_PYAUTOGUI_AVAILABLE", True)
    monkeypatch.setattr(ac.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ac, "_looks_like_path", lambda target: False)
    monkeypatch.setattr(ac, "_open_visibly_via_start_menu",
                        lambda app_name: f"Launched: {app_name} (opened visibly via the Start menu)")

    undo_stack = UndoStack()
    tool = ac.build_open_tool(undo_stack)

    result = tool.run(target="WhatsApp")

    assert result.startswith("Launched:")
    assert len(undo_stack._entries) == 1
