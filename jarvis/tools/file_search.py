import os
from pathlib import Path

from jarvis.tools.base import PermissionTier, Tool


def _search_files(query: str, root: str, max_results: int) -> str:
    search_root = Path(root).expanduser()
    if not search_root.exists():
        return f"Search root does not exist: {search_root}"

    query_lower = query.lower()
    matches = []
    for dirpath, dirnames, filenames in os.walk(search_root):
        # Skip noisy/system directories to keep search fast and relevant.
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d.lower() not in
                       {"node_modules", "$recycle.bin", "windows", "system32"}]
        for name in filenames + dirnames:
            if query_lower in name.lower():
                matches.append(str(Path(dirpath) / name))
                if len(matches) >= max_results:
                    break
        if len(matches) >= max_results:
            break

    if not matches:
        return f"No files or folders matching '{query}' found under {search_root}."
    header = f"Found {len(matches)} result(s) for '{query}' under {search_root}:"
    return header + "\n" + "\n".join(matches)


def build_tool(default_root: str, max_results: int) -> Tool:
    return Tool(
        name="search_files",
        description=(
            "Search for files or folders by (partial) name under a given directory. "
            "Use this before reading a file if you don't have its exact path."
        ),
        tier=PermissionTier.READ,
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Text to match in file/folder names."},
                "root": {
                    "type": "string",
                    "description": f"Directory to search under. Defaults to '{default_root}'.",
                },
            },
            "required": ["query"],
        },
        handler=lambda query, root=default_root: _search_files(query, root, max_results),
    )
