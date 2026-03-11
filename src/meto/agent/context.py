from __future__ import annotations

import logging
import os
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from meto.agent.exceptions import ContextForkError
from meto.agent.session import Session, SessionHistory, SessionLogger, generate_session_id
from meto.agent.todo import TodoManager

logger = logging.getLogger(__name__)

ToolHandler = Callable[[Any, dict[str, Any]], str]


@dataclass(frozen=True)
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

        # Ensure name in schema matches handler name if possible (not a lambda or closure)
        schema_name = self.schema["function"]["name"]
        handler_name = getattr(self.handler, "__name__", None)
        if (
            handler_name
            and handler_name != "<lambda>"
            and not handler_name.startswith("_")
            and handler_name != schema_name
            and handler_name != f"handle_{schema_name}"
        ):
            logger.warning(
                "PendingTool name mismatch: schema name '%s' != handler name '%s'",
                schema_name,
                handler_name,
            )


@dataclass
class Context:
    """Context object passed to tools that need it."""

    todos: TodoManager
    _history: list[dict[str, Any]] | SessionHistory = field(default_factory=list)
    _pending_tools: list[PendingTool] = field(default_factory=list)
    active_skill: str | None = None  # Track currently loaded skill for skill-local agents
    _session: Session | None = None
    _parent: Context | None = None
    context_id: str | None = None
    # Additional fields can be added as tool requirements evolve

    def __init__(
        self,
        todos: TodoManager,
        history: list[dict[str, Any]] | SessionHistory | None = None,
        pending_tools: list[PendingTool] | None = None,
        active_skill: str | None = None,
        session: Session | None = None,
        parent: Context | None = None,
        context_id: str | None = None,
    ) -> None:
        if not isinstance(todos, TodoManager):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("todos must be a TodoManager")
        self.todos = todos
        self._history = history if history is not None else []
        self._pending_tools = pending_tools if pending_tools is not None else []
        for tool in self._pending_tools:
            if not isinstance(tool, PendingTool):  # pyright: ignore[reportUnnecessaryIsInstance]
                raise TypeError("pending_tools must contain PendingTool instances")
        self.active_skill = active_skill
        self._session = session
        self._parent = parent
        self.context_id = context_id

    @property
    def history(self) -> Sequence[dict[str, Any]]:
        """Return an immutable view of the conversation history."""
        # Using tuple() provides a snapshot; for a live read-only view,
        # we could use a custom Sequence implementation, but tuple is safer
        # against concurrent modification of the underlying list during iteration.
        return tuple(self._history)

    @property
    def pending_tools(self) -> tuple[PendingTool, ...]:
        """Return an immutable view of the pending tools."""
        return tuple(self._pending_tools)

    @property
    def session(self) -> Session | None:
        """Return the active session."""
        return self._session

    @property
    def parent(self) -> Context | None:
        """Return the parent context."""
        return self._parent

    def add_message(self, message: dict[str, Any]) -> None:
        """Add a message to the conversation history."""
        self._history.append(message)

    def add_pending_tool(self, tool: PendingTool) -> None:
        """Add a tool to be injected on the next turn."""
        if not isinstance(tool, PendingTool):  # pyright: ignore[reportUnnecessaryIsInstance]
            raise TypeError("tool must be a PendingTool")
        self._pending_tools.append(tool)

    def clear_pending_tools(self) -> None:
        """Clear all pending tools."""
        self._pending_tools.clear()

    def fork(self) -> Context:
        """Create a forked context for subagents, preserving necessary state.

        Design Rationale:
        - History: Fresh for subagents to provide isolation and prevent context bloat.
        - Todos: Shared to maintain a single source of truth for task progress.
        - Active Skill: Preserved to allow skill-local subagents to function.
        - Pending Tools: Not preserved to ensure tool registration is explicit.
        - Session Logging: Hierarchical - child sessions log to parent's children/ directory
          for organized multi-level session history.

        Returns:
            A new Context instance with shared state where appropriate.
        """

        child_id = generate_session_id()
        child_history: list[dict[str, Any]] | SessionHistory = []

        if self._session and isinstance(self._history, SessionHistory):
            try:
                parent_logger = self._history.session_logger
                child_log_dir = parent_logger.log_dir / "children" / child_id
                child_logger = SessionLogger(child_id, log_dir=child_log_dir)

                child_logger.log_header(
                    {
                        "session_id": child_id,
                        "parent_id": self.context_id,
                        "working_dir": os.fspath(self._session.working_dir)
                        if self._session
                        else None,
                    }
                )
                child_history = SessionHistory(child_logger)
            except Exception as e:
                raise ContextForkError(f"Failed to create forked logging context: {e}") from e

        return Context(
            todos=self.todos,  # Share the same todo manager for centralized task tracking
            history=child_history,  # Start with fresh history for subagent
            pending_tools=[],
            active_skill=self.active_skill,  # Preserve active skill in forks
            session=self._session,
            parent=self,
            context_id=child_id,
        )
