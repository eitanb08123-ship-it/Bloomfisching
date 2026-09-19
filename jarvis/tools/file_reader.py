from pathlib import Path

from jarvis.tools.base import PermissionTier, Tool

TEXT_EXTENSIONS = {
    ".txt", ".md", ".json", ".csv", ".log", ".py", ".js", ".ts", ".html",
    ".css", ".yaml", ".yml", ".ini", ".cfg", ".xml",
}


def _read_file(path: str, max_bytes: int) -> str:
    file_path = Path(path).expanduser()
    if not file_path.exists() or not file_path.is_file():
        return f"File not found: {file_path}"
    if file_path.suffix.lower() not in TEXT_EXTENSIONS:
        return (
            f"Refusing to read '{file_path.suffix}' files for safety; only plain-text "
            f"file types are supported ({', '.join(sorted(TEXT_EXTENSIONS))})."
        )

    size = file_path.stat().st_size
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read(max_bytes)

    if size > max_bytes:
        content += f"\n\n[...truncated, file is {size} bytes, showed first {max_bytes}...]"
    return content


def build_tool(max_bytes: int) -> Tool:
    return Tool(
        name="read_file",
        description="Read the text content of a specific file the user points to (by path).",
        tier=PermissionTier.READ,
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Full path to the file."}},
            "required": ["path"],
        },
        handler=lambda path: _read_file(path, max_bytes),
    )
