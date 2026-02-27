from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from meto.agent.todo import TodoManager

ToolHandler = Callable[[Any, dict[str, Any]], str]


@dataclass
class PendingTool:
    """Tool staged for runtime injection on the next loop turn."""

    schema: dict[str, Any]
    handler: ToolHandler


@dataclass
class Context:
    """Context object passed to tools that need it."""

    todos: TodoManager
    history: list[dict[str, str | dict[str, Any]]]
    pending_tools: list[PendingTool] = field(default_factory=list)
    # Add more fields as needed for tools (e.g. session state, config, etc.)

    def fork(self) -> "Context":
        """Create a forked context for subagents, preserving necessary state."""
        return Context(
            todos=self.todos,  # Share the same todo manager for centralized task tracking
            history=[],  # Start with fresh history for subagent
            pending_tools=[],
        )
