"""Pydantic models for log viewer API responses."""

from datetime import datetime

from pydantic import BaseModel


class LogEntry(BaseModel):
    """A single log entry from the agent reasoning log."""

    timestamp: datetime
    level: str
    agent_name: str
    turn: int | None
    message: str


class LogFile(BaseModel):
    """Metadata about a log file."""

    filename: str
    size: int  # bytes
    modified: datetime


class TokenUsage(BaseModel):
    """Token usage statistics."""

    prompt: int
    cached: int
    completion: int
