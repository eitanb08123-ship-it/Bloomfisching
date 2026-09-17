import re
import urllib.parse
import urllib.request

from jarvis.tools.base import PermissionTier, Tool

_RESULT_PATTERN = re.compile(
    r'class="result__a"[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>.*?'
    r'class="result__snippet"[^>]*>(?P<snippet>.*?)</a>',
    re.S,
)


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html).strip()


def _resolve_link(href: str) -> str:
    """DuckDuckGo's HTML result links are redirects like
    '//duckduckgo.com/l/?uddg=<encoded-real-url>&rut=...' - pull the real URL
    out of the uddg param, falling back to the raw href if that fails."""
    parsed = urllib.parse.urlparse(href if "://" in href else f"https:{href}")
    query = urllib.parse.parse_qs(parsed.query)
    if "uddg" in query:
        return urllib.parse.unquote(query["uddg"][0])
    return href


def _search_web(query: str, max_results: int) -> str:
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (JARVIS assistant)"})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            html = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return f"Web search failed (no internet access, or DuckDuckGo is unreachable): {exc}"

    results = []
    for match in _RESULT_PATTERN.finditer(html):
        title = _strip_tags(match.group("title"))
        snippet = _strip_tags(match.group("snippet"))
        link = _resolve_link(match.group("href"))
        if title:
            results.append(f"- {title}\n  {snippet}\n  {link}")
        if len(results) >= max_results:
            break

    if not results:
        return f"No web results found for '{query}' (or DuckDuckGo changed their page layout)."
    return f"Top web results for '{query}':\n" + "\n".join(results)


def build_tool(max_results: int = 5) -> Tool:
    return Tool(
        name="web_search",
        description=(
            "Search the web (DuckDuckGo) for a query and return the top result titles, snippets, "
            "and links. Use this whenever the user asks you to look something up, research a topic, "
            "or find information online."
        ),
        tier=PermissionTier.READ,
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for."}},
            "required": ["query"],
        },
        handler=lambda query: _search_web(query, max_results),
    )
