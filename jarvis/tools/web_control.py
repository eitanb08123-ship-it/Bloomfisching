import webbrowser

from jarvis.tools.base import PermissionTier, Tool


def _open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    opened = webbrowser.open(url)
    return f"Opened in browser: {url}" if opened else f"Could not open browser for: {url}"


def build_tool() -> Tool:
    return Tool(
        name="open_website",
        description="Open a website URL in the default web browser.",
        tier=PermissionTier.ACTION,
        parameters={
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL or domain to open."}},
            "required": ["url"],
        },
        handler=lambda url: _open_url(url),
    )
