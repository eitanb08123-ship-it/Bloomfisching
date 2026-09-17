import os
import platform
import subprocess

import psutil

from jarvis.tools.base import PermissionTier, Tool


def _open_application(target: str) -> str:
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


def build_open_tool() -> Tool:
    return Tool(
        name="open_application",
        description="Open an application, file, or folder by name or path (e.g. 'notepad', 'chrome', a document path).",
        tier=PermissionTier.ACTION,
        parameters={
            "type": "object",
            "properties": {"target": {"type": "string", "description": "App name, or file/folder path."}},
            "required": ["target"],
        },
        handler=lambda target: _open_application(target),
    )


def build_close_tool() -> Tool:
    return Tool(
        name="close_application",
        description="Force-close a running application by process name. May lose unsaved work in that app.",
        tier=PermissionTier.CRITICAL,
        parameters={
            "type": "object",
            "properties": {"process_name": {"type": "string", "description": "e.g. 'notepad.exe', 'chrome'."}},
            "required": ["process_name"],
        },
        handler=lambda process_name: _close_application(process_name),
    )
