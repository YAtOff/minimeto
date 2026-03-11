"""Registry for non-essential tools discoverable at runtime."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

ToolHandler = Callable[[Any, dict[str, Any]], str]


@dataclass(frozen=True)
class ToolRegistration:
    """Runtime registration for a discoverable tool."""

    name: str
    schema: dict[str, Any]
    description: str
    handler: ToolHandler

    def __post_init__(self) -> None:
        """Validate registration metadata."""
        if not self.name:
            raise ValueError("Tool name cannot be empty")

        if not callable(self.handler):
            raise ValueError("Handler must be callable")

        schema_name = self.schema.get("function", {}).get("name")
        if schema_name != self.name:
            raise ValueError(f"Tool name mismatch: '{self.name}' != '{schema_name}' in schema")


class ToolRegistry:
    """Manages extra tools and provides simple keyword search."""

    def __init__(self) -> None:
        self.catalog: dict[str, ToolRegistration] = {}

    def register_tool(
        self,
        name: str,
        schema: dict[str, Any],
        handler: ToolHandler,
        description: str,
        *,
        allow_overwrite: bool = False,
    ) -> None:
        if name in self.catalog:
            existing = self.catalog[name]
            if (
                existing.handler == handler
                and existing.schema == schema
                and existing.description == description
            ):
                # Perfectly fine to re-register the exact same tool
                return

            if not allow_overwrite:
                logger.warning(
                    "Tool '%s' already registered in registry with different implementation. "
                    "Skipping registration. Use allow_overwrite=True to force overwrite.",
                    name,
                )
                return

            logger.warning("Overwriting existing tool registration in registry: %s", name)

        self.catalog[name] = ToolRegistration(
            name=name,
            schema=schema,
            description=description,
            handler=handler,
        )

    def register_from_mcp(
        self,
        tools: list[Any],
        call_tool: Callable[[str, dict[str, Any]], str],
    ) -> None:
        """Register MCP tools in the runtime catalog.

        The provided ``tools`` are expected to expose ``name``, ``description``,
        and ``inputSchema`` attributes (as returned by FastMCP client APIs).
        """
        for tool in tools:
            name = str(getattr(tool, "name", "")).strip()
            if not name:
                logger.warning("Skipping MCP tool with missing name: %s", tool)
                continue

            description = str(getattr(tool, "description", "") or "").strip()
            if not description:
                logger.warning("MCP tool '%s' has missing description", name)

            input_schema = getattr(tool, "inputSchema", None)
            if not isinstance(input_schema, dict):
                logger.warning(
                    "MCP tool '%s' has invalid inputSchema (expected dict, got %s). Using default empty schema.",
                    name,
                    type(input_schema).__name__,
                )
                input_schema = {"type": "object", "properties": {}}

            schema = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": input_schema,
                },
            }

            def _mcp_handler(
                _context: Any,
                parameters: dict[str, Any],
                *,
                _tool_name: str = name,
            ) -> str:
                return call_tool(_tool_name, parameters)

            self.register_tool(
                name=name,
                schema=schema,
                handler=_mcp_handler,
                description=description,
            )

    def search(self, query: str, top_k: int = 3) -> list[ToolRegistration]:
        """Search for tools by keyword matching.

        Scoring algorithm:
            - Token match in tool name: +3 points
            - Token match in description: +1 point
            - Results sorted by (score desc, name asc)

        Args:
            query: Search query (space-separated tokens)
            top_k: Maximum number of results to return

        Returns:
            Up to top_k tools ranked by relevance score.
        """
        if not query.strip():
            return []

        tokens = [token for token in query.lower().split() if token]
        if not tokens:
            return []

        scored: list[tuple[int, ToolRegistration]] = []
        for tool in self.catalog.values():
            haystack_name = tool.name.lower()
            haystack_description = tool.description.lower()

            score = 0
            for token in tokens:
                if token in haystack_name:
                    score += 3
                if token in haystack_description:
                    score += 1

            if score > 0:
                scored.append((score, tool))

        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [tool for _, tool in scored[: max(1, top_k)]]


registry = ToolRegistry()
