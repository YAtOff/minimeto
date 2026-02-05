"""Session persistence for meto agent."""

from __future__ import annotations

import json
import logging
import random
import threading
from abc import ABC, abstractmethod
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


class SessionLogger(ABC):
    """Base class for session loggers."""

    session_id: str

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id

    @abstractmethod
    def log_user(self, content: str) -> None:
        del content
        raise NotImplementedError

    @abstractmethod
    def log_assistant(self, content: str | None, tool_calls: list[Any] | None) -> None:
        del content
        del tool_calls
        raise NotImplementedError

    @abstractmethod
    def log_tool(self, tool_call_id: str, content: str) -> None:
        del tool_call_id
        del content
        raise NotImplementedError


class NullSessionLogger(SessionLogger):
    """No-op session logger."""

    def __init__(self, session_id: str) -> None:
        super().__init__(session_id)

    @override
    def log_user(self, content: str) -> None:
        pass

    @override
    def log_assistant(self, content: str | None, tool_calls: list[Any] | None) -> None:
        pass

    @override
    def log_tool(self, tool_call_id: str, content: str) -> None:
        pass


class FileSessionLogger(SessionLogger):
    """Append-only JSONL logger for chat history persistence."""

    def __init__(
        self, session_id: str | None = None, session_dir: Path = settings.SESSION_DIR
    ) -> None:
        self.session_id: str = session_id or generate_session_id()
        super().__init__(self.session_id)
        self.session_file: Path = session_dir / f"session-{self.session_id}.jsonl"
        self._lock: threading.Lock = threading.Lock()

        # Ensure parent directory exists
        self.session_file.parent.mkdir(parents=True, exist_ok=True)

    def _append(self, message: dict[str, Any]) -> None:
        """Thread-safe append to JSONL file."""
        with self._lock:
            with open(self.session_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(message, ensure_ascii=False) + "\n")

    @override
    def log_user(self, content: str) -> None:
        """Log user message with timestamp."""
        msg = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "role": "user",
            "content": content,
            "session_id": self.session_id,
        }
        self._append(msg)

    @override
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

    @override
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


def load_session(session_id: str, session_dir: Path = settings.SESSION_DIR) -> list[dict[str, Any]]:
    """Load conversation history from session file.

    Returns OpenAI-style history list (no timestamps/session_id wrapper).
    """
    session_file = session_dir / f"session-{session_id}.jsonl"

    if not session_file.exists():
        return []

    messages = []
    try:
        with open(session_file, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    raw = json.loads(line)
                    # Extract OpenAI message format, strip metadata
                    msg: dict[str, Any] = {"role": raw["role"], "content": raw.get("content")}
                    if "tool_calls" in raw:
                        msg["tool_calls"] = raw["tool_calls"]
                    if "tool_call_id" in raw:
                        msg["tool_call_id"] = raw["tool_call_id"]
                    messages.append(msg)
    except (OSError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load session {session_id}: {e}")
        return []

    return messages


def list_session_files(session_dir: Path = settings.SESSION_DIR) -> list[Path]:
    """Return list of session-*.jsonl files, sorted by mtime (newest first)."""
    if not session_dir.exists():
        return []
    return sorted(
        session_dir.glob("session-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def get_session_info(path: Path) -> dict[str, Any]:
    """Return session metadata: id, created, modified, size, message_count."""
    stat = path.stat()
    message_count = 0
    try:
        with open(path, encoding="utf-8") as f:
            message_count = sum(1 for _ in f)
    except OSError:
        message_count = 0

    return {
        "id": path.stem.replace("session-", ""),
        "path": str(path),
        "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "size": stat.st_size,
        "message_count": message_count,
    }


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


class Session:
    """Wraps session_id, history and session_logger for unified session management."""

    session_id: str
    history: SessionHistory
    session_logger_cls: type[SessionLogger]
    session_logger: SessionLogger

    def __init__(
        self,
        sid: str | None = None,
        session_logger_cls: type[SessionLogger] | None = None,
    ) -> None:
        self.session_logger_cls = session_logger_cls or FileSessionLogger
        if sid:
            self.session_id = sid
            self.session_logger = self.session_logger_cls(sid)
            self.history = SessionHistory(self.session_logger, load_session(sid))
        else:
            self.session_id = generate_session_id()
            self.session_logger = self.session_logger_cls(self.session_id)
            self.history = SessionHistory(self.session_logger)
