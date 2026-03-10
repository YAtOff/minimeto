"""Session persistence for meto agent."""

from __future__ import annotations

import json
import logging
import os
import random
import re
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from meto.conf import settings


@dataclass
class Node:
    message: dict[str, Any]
    parent: Node | None = None
    children: list[Node] = field(default_factory=list)


logger = logging.getLogger("agent")


def generate_session_id() -> str:
    """Generate timestamp-based session ID: {timestamp}-{random_suffix}."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    return f"{timestamp}-{random_suffix}"


class SessionLogger:
    """Append-only JSONL logger for chat history persistence."""

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


class SessionHistory(list[dict[str, Any]]):
    """List that auto-logs appends to session_logger."""

    _session_logger: SessionLogger
    checkpoints: dict[str, Node]
    head: Node | None

    def __init__(
        self,
        session_logger: SessionLogger,
        head: Node | None = None,
        checkpoints: dict[str, Node] | None = None,
    ) -> None:
        self._session_logger = session_logger
        self.head = head
        self.checkpoints = checkpoints or {}
        super().__init__([node.message for node in self._get_active_path()])

    def _get_active_path(self) -> list[Node]:
        curr = self.head
        path: list[Node] = []
        while curr:
            path.append(curr)
            curr = curr.parent
        path.reverse()
        return path

    @override
    def append(self, item: dict[str, Any]) -> None:
        node = Node(item, parent=self.head)
        if self.head:
            self.head.children.append(node)
        self.head = node

        super().append(item)

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
        """Create a checkpoint at the current history state."""
        if self.head:
            self.checkpoints[name] = self.head
            self._session_logger.log_checkpoint(name)

    def log_rewind(self, name: str) -> bool:
        """Rewind history to the specified checkpoint.

        Returns:
            True if checkpoint was found and rewound, False otherwise.
        """
        if name not in self.checkpoints:
            return False

        self.head = self.checkpoints[name]
        self.clear()
        self.extend([node.message for node in self._get_active_path()])

        self._session_logger.log_rewind(name)
        return True


class Session:
    """Wraps session_id, history and session_logger for unified session management."""

    session_id: str
    working_dir: Path
    history: SessionHistory

    @classmethod
    def load(cls, session_id: str, session_dir: Path = settings.SESSION_DIR) -> Session:
        """Load session by ID, returning Session instance.

        If a compact marker exists in the session file, only messages after
        the last compact marker are loaded. The full history is preserved on disk.
        """
        from meto.agent.exceptions import SessionNotFoundError
        from meto.agent.permissions import PermissionManager

        PermissionManager.reset()

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
        skipped_count = 0
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
                            skipped_count += 1
                            continue

            # Second pass: construct history tree (skip header + pre-compact messages)
            for i, raw in lines:
                if i == 0:
                    info = {
                        "working_dir": raw.get("working_dir", os.fspath(Path.cwd())),
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
                if head:
                    head.children.append(new_node)
                head = new_node
                messages_loaded += 1

            if last_compact_index >= 0:
                logger.info(
                    f"Session {session_id}: compact marker at line {last_compact_index}, "
                    f"loading messages after compact"
                )

            if skipped_count > 0:
                logger.warning(
                    f"Session {session_id}: skipped {skipped_count} malformed lines. "
                    "History may be incomplete."
                )

        except OSError as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return cls.new()

        working_dir = Path(info.get("working_dir", os.fspath(Path.cwd())))
        os.chdir(working_dir)
        session_logger = SessionLogger(session_id, session_file=session_file, log_dir=log_dir)
        history = SessionHistory(session_logger, head=head, checkpoints=checkpoints)
        return cls(session_id=session_id, working_dir=working_dir, history=history)

    @classmethod
    def new(cls) -> Session:
        """Create new session with unique ID."""
        from meto.agent.permissions import PermissionManager

        PermissionManager.reset()

        session_id = generate_session_id()
        working_dir = Path.cwd()
        log_dir = settings.SESSION_DIR / session_id
        session_logger = SessionLogger(session_id, log_dir=log_dir)
        session_logger.log_header(
            {
                "session_id": session_id,
                "working_dir": os.fspath(working_dir),
            }
        )
        history = SessionHistory(session_logger, head=None, checkpoints={})
        return cls(session_id=session_id, working_dir=working_dir, history=history)

    def __init__(
        self,
        session_id: str,
        working_dir: Path,
        history: SessionHistory,
    ) -> None:
        self.session_id = session_id
        self.working_dir = working_dir
        self.history = history

    def compact(self, summary: str) -> None:
        """Log a compact marker to truncate history on next load.

        Args:
            summary: Human-readable summary of the conversation so far

        The full history is preserved on disk, but when this session is
        reloaded, messages before this marker will be skipped.
        """
        self.history.log_compact(summary)
