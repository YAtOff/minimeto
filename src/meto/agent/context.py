from dataclasses import dataclass
from typing import Any

from meto.agent.todo import TodoManager


@dataclass
class Context:
    """Context object passed to tools that need it."""

    todos: TodoManager
    history: list[dict[str, str | dict[str, Any]]]
    # Add more fields as needed for tools (e.g. session state, config, etc.)

    def fork(self) -> "Context":
        """Create a forked context for subagents, preserving necessary state."""
        return Context(
            todos=self.todos,  # Share the same todo manager for centralized task tracking
            history=[],  # Start with fresh history for subagent
        )
