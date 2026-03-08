from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from meto.agent.todo import TodoManager

ToolHandler = Callable[[Any, dict[str, Any]], str]


@dataclass
class PendingTool:
    """Tool staged for runtime injection on the next loop turn."""

    schema: dict[str, Any]
    handler: ToolHandler

    def __post_init__(self) -> None:
        """Validate the tool schema structure."""
        if "function" not in self.schema:
            raise ValueError("PendingTool schema must contain 'function' key")
        if "name" not in self.schema["function"]:
            raise ValueError("PendingTool schema must contain 'function.name'")
        if not callable(self.handler):
            raise ValueError("PendingTool handler must be callable")


@dataclass
class Context:
    """Context object passed to tools that need it."""

    todos: TodoManager
    _history: list[dict[str, Any]] = field(default_factory=list)
    pending_tools: list[PendingTool] = field(default_factory=list)
    active_skill: str | None = None  # Track currently loaded skill for skill-local agents
    # Add more fields as needed for tools (e.g. session state, config, etc.)

    def __init__(
        self,
        todos: TodoManager,
        history: list[dict[str, Any]] | None = None,
        pending_tools: list[PendingTool] | None = None,
        active_skill: str | None = None,
    ) -> None:
        self.todos = todos
        self._history = history if history is not None else []
        self.pending_tools = pending_tools if pending_tools is not None else []
        self.active_skill = active_skill

    @property
    def history(self) -> Sequence[dict[str, Any]]:
        """Return an immutable view of the conversation history."""
        # Using tuple() provides a snapshot; for a live read-only view,
        # we could use a custom Sequence implementation, but tuple is safer
        # against concurrent modification of the underlying list during iteration.
        return tuple(self._history)

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the conversation history."""
        self._history.append(message)

    def fork(self) -> "Context":
        """Create a forked context for subagents, preserving necessary state.

        Design Rationale:
        - History: Fresh for subagents to provide isolation and prevent context bloat.
        - Todos: Shared to maintain a single source of truth for task progress.
        - Active Skill: Preserved to allow skill-local subagents to function.
        - Pending Tools: Not preserved to ensure tool registration is explicit.

        Returns:
            A new Context instance with shared state where appropriate.
        """
        return Context(
            todos=self.todos,  # Share the same todo manager for centralized task tracking
            history=[],  # Start with fresh history for subagent
            pending_tools=[],
            active_skill=self.active_skill,  # Preserve active skill in forks
        )
