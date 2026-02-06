from dataclasses import dataclass
from typing import Any

from meto.agent.todo import TodoManager


@dataclass
class Context:
    """Context object passed to tools that need it."""

    todos: TodoManager
    history: list[dict[str, str | dict[str, Any]]]
    # Add more fields as needed for tools (e.g. session state, config, etc.)
