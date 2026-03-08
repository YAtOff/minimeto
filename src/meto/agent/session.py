"""Session persistence for meto agent."""

from __future__ import annotations

import json
import logging
import os
import random
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override

from meto.conf import settings

logger = logging.getLogger("agent")


def generate_session_id() -> str:
    """Generate timestamp-based session ID: {timestamp}-{random_suffix}."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    return f"{timestamp}-{random_suffix}"


class SessionLogger:
    """Append-only JSONL logger for chat history persistence."""

    def __init__(self, session_id: str, session_dir: Path = settings.SESSION_DIR) -> None:
        self.session_id: str = session_id
        self.session_file: Path = session_dir / f"session-{self.session_id}.jsonl"
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
        """Log compact marker with summary.

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


class SessionHistory(list[dict[str, Any]]):
    """List that auto-logs appends to session_logger."""

    _session_logger: SessionLogger

    def __init__(
        self, session_logger: SessionLogger, initial_data: list[dict[str, Any]] | None = None
    ) -> None:
        super().__init__(initial_data or [])
        self._session_logger = session_logger

    @override
    def append(self, item: dict[str, Any]) -> None:
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
        from meto.agent.permissions import PermissionManager

        PermissionManager.reset()

        session_file = session_dir / f"session-{session_id}.jsonl"

        if not session_file.exists():
            return cls.new()  # Return new session if file doesn't exist

        info = {}
        messages = []
        last_compact_index = -1

        # First pass: read all lines and find last compact marker
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
                            continue

            # Second pass: extract messages (skip header + pre-compact messages)
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

                # Extract OpenAI message format, strip metadata
                msg: dict[str, Any] = {"role": raw["role"], "content": raw.get("content")}
                if "tool_calls" in raw:
                    msg["tool_calls"] = raw["tool_calls"]
                if "tool_call_id" in raw:
                    msg["tool_call_id"] = raw["tool_call_id"]
                messages.append(msg)

            if last_compact_index >= 0:
                logger.info(
                    f"Session {session_id}: compact marker at line {last_compact_index}, "
                    f"loading {len(messages)} messages after compact"
                )

        except OSError as e:
            logger.error(f"Failed to load session {session_id}: {e}")
            return cls.new()

        working_dir = Path(info.get("working_dir", os.fspath(Path.cwd())))
        os.chdir(working_dir)
        session_logger = SessionLogger(session_id)
        history = SessionHistory(session_logger, initial_data=messages)
        return cls(session_id=session_id, working_dir=working_dir, history=history)

    @classmethod
    def new(cls) -> Session:
        """Create new session with unique ID."""
        from meto.agent.permissions import PermissionManager

        PermissionManager.reset()

        session_id = generate_session_id()
        working_dir = Path.cwd()
        session_logger = SessionLogger(session_id)
        session_logger.log_header(
            {
                "session_id": session_id,
                "working_dir": os.fspath(working_dir),
            }
        )
        history = SessionHistory(session_logger)
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
