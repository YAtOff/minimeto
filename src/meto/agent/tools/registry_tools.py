"""Registry and tool discovery operations."""

from typing import Any, cast

from meto.agent.context import Context, PendingTool
from meto.agent.tool_registry import registry


def search_available_tools(context: Context, query: str, top_k: int = 3) -> str:
    """Search registry tools and stage selected tools for next loop turn."""
    results = registry.search(query, top_k=top_k)
    if not results:
        return "No matching tools found."

    pending_names = {
        pending_tool.schema.get("function", {}).get("name")
        for pending_tool in context.pending_tools
    }

    lines: list[str] = []
    for tool in results:
        if tool.name not in pending_names:
            context.pending_tools.append(PendingTool(schema=tool.schema, handler=tool.handler))
            pending_names.add(tool.name)
        lines.append(f"{tool.name}: {tool.description}")

    return "\n".join(lines)


def handle_search_available_tools(context: Context, parameters: dict[str, Any]) -> str:
    """Handle runtime tool discovery."""
    query = cast(str, parameters.get("query", ""))
    top_k = cast(int, parameters.get("top_k", 3))
    return search_available_tools(context, query, top_k)
