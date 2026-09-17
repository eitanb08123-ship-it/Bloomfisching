import os
import platform
import subprocess
import time

import psutil

from jarvis.tools.base import PermissionTier, Tool
from jarvis.utils.logger import get_logger

log = get_logger("tools.app_control")

try:
    import pyautogui

    _PYAUTOGUI_AVAILABLE = True
except ImportError:
    _PYAUTOGUI_AVAILABLE = False


def _looks_like_path(target: str) -> bool:
    return os.path.exists(target) or os.sep in target or "/" in target


def _open_visibly_via_start_menu(app_name: str) -> str:
    """Presses the Windows key and types the app name into Start Menu search,
    so the launch is visible on screen instead of happening silently. Only
    used for bare app names (not file/folder paths, which Start-menu search
    doesn't resolve reliably). Real keyboard input goes system-wide for
    ~1 second - opening the Start menu grabs focus itself, but avoid
    triggering this while typing something else at the exact same moment."""
    try:
        pyautogui.press("win")
        time.sleep(0.6)
        pyautogui.typewrite(app_name, interval=0.03)
        time.sleep(0.4)
        pyautogui.press("enter")
        return f"Launched: {app_name} (opened visibly via the Start menu)"
    except Exception as exc:
        log.warning("Visible launch failed for '%s', falling back to instant launch: %s", app_name, exc)
        return _open_application_instant(app_name)


def _open_application_instant(target: str) -> str:
    """Launch an application or file by name/path using the OS's normal
    association mechanism. No elevated privileges are requested; if Windows
    would show a UAC prompt for this target, it still will."""
    try:
        if platform.system() == "Windows":
            os.startfile(target)  # noqa: S606 - intentional, user-approved launch
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return f"Launched: {target}"
    except FileNotFoundError:
        return f"Could not find application or file: {target}"
    except OSError as exc:
        return f"Failed to launch '{target}': {exc}"


def _open_application(target: str) -> str:
    if _PYAUTOGUI_AVAILABLE and platform.system() == "Windows" and not _looks_like_path(target):
        return _open_visibly_via_start_menu(target)
    return _open_application_instant(target)


def _close_application(process_name: str) -> str:
    """Terminate running processes whose name matches. This can lose unsaved
    work in that application, which is why this tool is CRITICAL tier."""
    matched = []
    for proc in psutil.process_iter(["pid", "name"]):
        name = proc.info.get("name") or ""
        if process_name.lower() in name.lower():
            try:
                proc.terminate()
                matched.append(f"{name} (pid {proc.info['pid']})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    if not matched:
        return f"No running process matching '{process_name}' was found."
    return "Closed: " + ", ".join(matched)


def build_open_tool(undo_stack) -> Tool:
    def _handler(target: str) -> str:
        result = _open_application(target)
        if result.startswith("Launched:"):
            # Best-effort undo: closes whatever now matches that name. If the
            # user already had another instance of it open, this may close
            # that one instead - there's no handle to the exact process we
            # just launched (os.startfile doesn't hand one back).
            undo_stack.push("open_application", f"close '{target}' again", lambda: _close_application(target))
        return result

    return Tool(
        name="open_application",
        description="Open an application, file, or folder by name or path (e.g. 'notepad', 'chrome', a document path).",
        tier=PermissionTier.ACTION,
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string", "description": "App name, or file/folder path."}},
            "required": ["target"],
        },
        handler=_handler,
    )


def build_close_tool(undo_stack) -> Tool:
    def _reopen(process_name: str) -> str:
        reopened = _open_application(process_name)
        return f"{reopened} (any unsaved work from before the close could not be recovered)"

    def _handler(process_name: str) -> str:
        result = _close_application(process_name)
        if result.startswith("Closed:"):
            undo_stack.push("close_application", f"reopen '{process_name}'", lambda: _reopen(process_name))
        return result

    return Tool(
        name="close_application",
        description="Force-close a running application by process name. May lose unsaved work in that app.",
        tier=PermissionTier.CRITICAL,
        parameters={
            "type": "object",
            "properties": {"process_name": {"type": "string", "description": "e.g. 'notepad.exe', 'chrome'."}},
            "required": ["process_name"],
        },
        handler=_handler,
    )
