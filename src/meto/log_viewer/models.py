"""Pydantic models for the log viewer API.

These models define the structure of data returned by the log viewer endpoints.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class TokenUsage(BaseModel):
    """Token usage statistics for a log file or turn."""

    prompt: int
    cached: int
    completion: int


class LogFile(BaseModel):
    """Metadata for a log file."""

    filename: str
    size: int  # bytes
    modified: datetime


class LogEntry(BaseModel):
    """A single log entry from the JSONL file."""

    timestamp: datetime
    level: str  # INFO, DEBUG, ERROR, etc.
    agent_name: str | None
    turn: int | None
    message: str
