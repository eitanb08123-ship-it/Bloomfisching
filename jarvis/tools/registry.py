from jarvis.tools import (
    app_control,
    file_reader,
    file_search,
    memory_tools,
    system_info,
    undo_tool,
    web_control,
    web_search,
)
from jarvis.tools.base import Tool


class ToolRegistry:
    def __init__(self, settings: dict, memory_store, undo_stack):
        tools_cfg = settings["tools"]
        self._tools: dict[str, Tool] = {}

        for tool in [
            system_info.build_tool(),
            file_search.build_tool(tools_cfg["file_search_root"], tools_cfg["max_search_results"]),
            file_reader.build_tool(tools_cfg["max_file_read_bytes"]),
            app_control.build_open_tool(undo_stack),
            app_control.build_close_tool(undo_stack),
            web_control.build_tool(),
            web_search.build_tool(),
            memory_tools.build_remember_tool(memory_store, undo_stack),
            memory_tools.build_recall_tool(memory_store),
            memory_tools.build_forget_tool(memory_store, undo_stack),
            undo_tool.build_tool(undo_stack),
        ]:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def anthropic_schemas(self) -> list[dict]:
        return [t.to_anthropic_schema() for t in self._tools.values()]

    def openai_schemas(self) -> list[dict]:
        return [t.to_openai_schema() for t in self._tools.values()]
