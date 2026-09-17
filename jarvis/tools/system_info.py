import platform

import psutil

from jarvis.tools.base import PermissionTier, Tool


def _get_system_info() -> str:
    cpu_percent = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    disks = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(
                f"{part.device} ({part.mountpoint}): {usage.percent}% used, "
                f"{usage.free // (1024**3)} GB free"
            )
        except (PermissionError, OSError):
            continue

    lines = [
        f"OS: {platform.system()} {platform.release()}",
        f"CPU usage: {cpu_percent}%",
        f"RAM: {mem.percent}% used ({mem.used // (1024**2)} MB / {mem.total // (1024**2)} MB)",
        "Disks:",
        *[f"  - {d}" for d in disks],
    ]
    return "\n".join(lines)


def build_tool() -> Tool:
    return Tool(
        name="get_system_info",
        description="Get current CPU usage, RAM usage, and disk usage of the computer.",
        tier=PermissionTier.READ,
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda: _get_system_info(),
    )
