"""Registry for non-essential tools discoverable at runtime."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

ToolHandler = Callable[[Any, dict[str, Any]], str]


@dataclass(frozen=True)
class ToolRegistration:
    """Runtime registration for a discoverable tool."""

    name: str
    schema: dict[str, Any]
    description: str
    handler: ToolHandler


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
    ) -> None:
        self.catalog[name] = ToolRegistration(
            name=name,
            schema=schema,
            description=description,
            handler=handler,
        )

    def search(self, query: str, top_k: int = 3) -> list[ToolRegistration]:
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
