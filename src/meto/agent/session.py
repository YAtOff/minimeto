"""Session persistence for meto agent."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from meto.agent.exceptions import SessionNotFoundError
from meto.conf import settings


@dataclass
class Node:
    message: dict[str, Any]
    parent: Node | None = field(default=None, repr=False)
    _children: list[Node] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        # Validate message structure
        if "role" not in self.message:
            raise ValueError("message must have 'role' field")

        # Prevent cycles
        if self.parent is self:
            raise ValueError("Node cannot be its own parent")

        if self.parent:
            self.parent.add_child(self)

    @property
    def children(self) -> tuple[Node, ...]:
        """Immutable view of child nodes."""
        return tuple(self._children)

    def add_child(self, child: Node) -> None:
        """Add a child node while ensuring tree invariants."""
        if child in self._children:
            return
        if child.parent is not None and child.parent is not self:
            raise ValueError("Child already has a different parent")
        self._children.append(child)
        child.parent = self


logger = logging.getLogger("agent")


def generate_session_id() -> str:
    """Generate timestamp-based session ID.

    Format: {timestamp}-{random_suffix}
    Example: 20240310_143052-abc123

    The format must match the regex ^[a-zA-Z0-9_\\-]+$ for validation.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    return f"{timestamp}-{random_suffix}"


class SessionLogger:
    """Append-only JSONL logger for chat history persistence.

    Each session gets its own directory (log_dir) containing log.jsonl.
    Child sessions are nested under log_dir/children/{child_id}/ for
    hierarchical organization.
    """

    log_dir: Path

    def __init__(
        self, session_id: str, session_file: Path | None = None, log_dir: Path | None = None
    ) -> None:
        self.session_id: str = session_id
        self.log_dir = log_dir or (settings.SESSION_DIR / session_id)
        self.session_file: Path = session_file or (self.log_dir / "log.jsonl")
        self._lock: threading.Lock = threading.Lock()
        self._header_logged: bool = False

        # Ensure parent directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, message: dict[str, Any]) -> None:
        """Thread-safe append to JSONL file."""
        with self._lock:
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")

    def log_header(self, header: dict[str, Any]) -> None:
        """Log session header with metadata."""
        if not self._header_logged:
            self._append(header)
            self._header_logged = True
        else:
            logger.warning(
                f"Header already logged for session {self.session_id}, skipping duplicate header."
            )

    def log_user(self, content: str) -> None:
        """Log user message with timestamp."""
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "user",
            "content": content,
            "session_id": self.session_id,
        }
        self._append(msg)

    def log_assistant(self, content: str | None, tool_calls: list[Any] | None) -> None:
        """Log assistant response with optional tool_calls."""
        msg: dict[str, Any] = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "assistant",
            "content": content,
            "session_id": self.session_id,
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        self._append(msg)

    def log_tool(self, tool_call_id: str, content: str) -> None:
        """Log tool execution result."""
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
            "session_id": self.session_id,
        }
        self._append(msg)

    def log_compact(self, summary: str) -> None:
        """Log a compact marker with summary.

        When a session is reloaded, all messages before the last compact
        marker will be skipped, reducing memory usage while preserving
        full history on disk.
        """
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "compact",
            "summary": summary,
            "session_id": self.session_id,
        }
        self._append(msg)

    def log_checkpoint(self, name: str) -> None:
        """Log a named checkpoint marker."""
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "checkpoint",
            "name": name,
            "session_id": self.session_id,
        }
        self._append(msg)

    def log_rewind(self, name: str) -> None:
        """Log a rewind marker to truncate history to a checkpoint."""
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "rewind",
            "to_checkpoint": name,
            "session_id": self.session_id,
        }
        self._append(msg)


class SessionHistory(Sequence[dict[str, Any]]):
    """Encapsulated history that maintains dual list/tree representations."""

    _session_logger: SessionLogger
    _checkpoints: dict[str, Node]
    _head: Node | None
    _history: list[dict[str, Any]]

    @property
    def session_logger(self) -> SessionLogger:
        """Return the underlying session logger."""
        return self._session_logger

    @property
    def head(self) -> Node | None:
        """Return the current head node in the history tree."""
        return self._head

    @property
    def checkpoints(self) -> dict[str, Node]:
        """Return the named checkpoints mapped to nodes."""
        return self._checkpoints

    def __init__(
        self,
        session_logger: SessionLogger,
        head: Node | None = None,
        checkpoints: dict[str, Node] | None = None,
    ) -> None:
        self._session_logger = session_logger
        self._head = head
        self._checkpoints = checkpoints or {}
        self._history = [node.message for node in self._get_active_path()]

    def _get_active_path(self) -> list[Node]:
        """Traverse from head to root to build the active message path.

        Returns:
            A reversed list of nodes from root to head, representing
            the current linear conversation history.
        """
        curr = self._head
        path: list[Node] = []
        while curr:
            path.append(curr)
            curr = curr.parent
        path.reverse()
        return path

    @override
    def __len__(self) -> int:
        return len(self._history)

    @override
    def __getitem__(self, index: Any) -> Any:
        return self._history[index]

    @override
    def __repr__(self) -> str:
        return f"SessionHistory({self._history!r})"

    @override
    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._history)

    def append(self, item: dict[str, Any]) -> None:
        """Add a message to history, maintaining tree and list representations."""
        node = Node(item, parent=self._head)
        self._head = node
        self._history.append(item)

        role = item.get("role")
        if role == "user":
            self._session_logger.log_user(item["content"])
        elif role == "assistant":
            self._session_logger.log_assistant(item.get("content"), item.get("tool_calls"))
        elif role == "tool":
            self._session_logger.log_tool(item["tool_call_id"], item["content"])

    def log_compact(self, summary: str) -> None:
        """Log a compact marker via the session logger."""
        self._session_logger.log_compact(summary)

    def log_checkpoint(self, name: str) -> None:
        """Create a checkpoint at the current history state.

        Stores a reference to the current head node, enabling efficient
        rewinding without copying or indexing into the history list.
        """
        if self._head:
            self._checkpoints[name] = self._head
            self._session_logger.log_checkpoint(name)

    def log_rewind(self, name: str) -> bool:
        """Rewind history to the specified checkpoint.

        Updates the head pointer to the checkpointed node and rebuilds
        the list view from the active path. The full tree is preserved
        on disk for potential alternate branch restoration.

        Returns:
            True if checkpoint was found and rewound, False otherwise.
        """
        if name not in self._checkpoints:
            return False

        self._head = self._checkpoints[name]
        # Rebuild history list view
        self._history = [node.message for node in self._get_active_path()]

        self._session_logger.log_rewind(name)
        return True


class Session:
    """Wraps session_id, history and session_logger for unified session management."""

    _session_id: str
    _working_dir: Path
    _history: SessionHistory
    _permissions: dict[str, bool]
    _yolo: bool

    @classmethod
    def load(
        cls, session_id: str, session_dir: Path = settings.SESSION_DIR, yolo: bool = False
    ) -> Session:
        """Load session by ID, returning Session instance.

        If a compact marker exists in the session file, only messages after
        the last compact marker are loaded. The full history is preserved on disk.
        """

        # Session ID validation moved to __init__ but kept here for early exit
        if not re.match(r"^[a-zA-Z0-9_\-]+$", session_id):
            raise ValueError(
                f"Invalid session ID format: '{session_id}'. "
                "Only alphanumeric characters, underscores and hyphens are allowed."
            )

        log_dir = session_dir / session_id
        session_file = log_dir / "log.jsonl"

        if not session_file.exists():
            raise SessionNotFoundError(f"Session '{session_id}' not found at {session_file}")

        info = {}
        last_compact_index = -1
        head: Node | None = None
        checkpoints: dict[str, Node] = {}
        messages_loaded = 0

        # First pass: read all lines and find last compact marker
        skipped_lines: list[int] = []
        try:
            lines: list[tuple[int, dict[str, Any]]] = []
            with open(session_file, encoding="utf-8") as f:
                for i, line in enumerate(f):
                    if line.strip():
                        try:
                            raw = json.loads(line)
                            lines.append((i, raw))
                            if raw.get("role") == "compact":
                                last_compact_index = i
                        except json.JSONDecodeError:
                            logger.warning(f"Skipping malformed line {i} in session {session_id}")
                            skipped_lines.append(i)
                            continue

            # Second pass: construct history tree (skip header + pre-compact messages)
            for i, raw in lines:
                if i == 0:
                    info = {
                        "working_dir": raw.get("working_dir", os.fspath(Path.cwd())),
                        "yolo": raw.get("yolo", False),
                    }
                    continue

                # Skip messages before the last compact marker
                if last_compact_index >= 0 and i <= last_compact_index:
                    continue

                # Skip compact markers themselves
                if raw.get("role") == "compact":
                    continue

                if raw.get("role") == "checkpoint":
                    name = raw.get("name")
                    if name and head:
                        checkpoints[name] = head
                    continue

                if raw.get("role") == "rewind":
                    name = raw.get("to_checkpoint")
                    if name and name in checkpoints:
                        head = checkpoints[name]
                    continue

                # Extract OpenAI message format, strip metadata
                msg: dict[str, Any] = {"role": raw["role"], "content": raw.get("content")}
                if "tool_calls" in raw:
                    msg["tool_calls"] = raw["tool_calls"]
                if "tool_call_id" in raw:
                    msg["tool_call_id"] = raw["tool_call_id"]

                new_node = Node(msg, parent=head)
                head = new_node
                messages_loaded += 1

            if last_compact_index >= 0:
                logger.info(
                    f"Session {session_id}: compact marker at line {last_compact_index}, "
                    f"loading messages after compact"
                )

            if skipped_lines:
                logger.error(
                    f"Session {session_id}: Failed to parse {len(skipped_lines)} lines "
                    f"(lines: {skipped_lines[:5]}{'...' if len(skipped_lines) > 5 else ''}). "
                    "History may be incomplete. Consider restoring from backup."
                )

        except OSError as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return cls.new(yolo=yolo)

        working_dir = Path(info.get("working_dir", os.fspath(Path.cwd())))
        os.chdir(working_dir)
        session_logger = SessionLogger(session_id, session_file=session_file, log_dir=log_dir)
        history = SessionHistory(session_logger, head=head, checkpoints=checkpoints)
        final_yolo = yolo or info.get("yolo", False)
        return cls(session_id=session_id, working_dir=working_dir, history=history, yolo=final_yolo)

    @classmethod
    def new(cls, yolo: bool = False) -> Session:
        """Create new session with unique ID."""
        session_id = generate_session_id()
        working_dir = Path.cwd()
        log_dir = settings.SESSION_DIR / session_id
        session_logger = SessionLogger(session_id, log_dir=log_dir)
        session_logger.log_header(
            {
                "session_id": session_id,
                "working_dir": os.fspath(working_dir),
                "yolo": yolo,
            }
        )
        history = SessionHistory(session_logger, head=None, checkpoints={})
        return cls(session_id=session_id, working_dir=working_dir, history=history, yolo=yolo)

    def __init__(
        self,
        session_id: str,
        working_dir: Path,
        history: SessionHistory,
        permissions: dict[str, bool] | None = None,
        yolo: bool = False,
    ) -> None:
        if not re.match(r"^[a-zA-Z0-9_\-]+$", session_id):
            raise ValueError(
                f"Invalid session ID format: '{session_id}'. "
                "Only alphanumeric characters, underscores and hyphens are allowed."
            )
        if not working_dir.exists():
            raise FileNotFoundError(f"Working directory does not exist: {working_dir}")

        self._session_id = session_id
        self._working_dir = working_dir
        self._history = history
        self._permissions = {}  # Explicitly initialize for basedpyright
        self.permissions = permissions or {}  # Uses setter for validation
        self._yolo = yolo

    @property
    def session_id(self) -> str:
        """Read-only session ID."""
        return self._session_id

    @property
    def working_dir(self) -> Path:
        """Read-only working directory."""
        return self._working_dir

    @property
    def history(self) -> SessionHistory:
        """Read-only history object."""
        return self._history

    @property
    def yolo(self) -> bool:
        """Global YOLO mode flag."""
        return self._yolo

    @yolo.setter
    def yolo(self, value: bool) -> None:
        self._yolo = value

    @property
    def permissions(self) -> dict[str, bool]:
        """Dictionary of session-scoped permissions."""
        return self._permissions

    @permissions.setter
    def permissions(self, value: dict[str, bool]) -> None:
        self._permissions = dict(value)  # Copy to prevent external mutation

    def compact(self, summary: str) -> None:
        """Log a compact marker to truncate history on next load.

        Args:
            summary: Human-readable summary of the conversation so far

        The full history is preserved on disk, but when this session is
        reloaded, messages before this marker will be skipped.
        """
        self.history.log_compact(summary)
