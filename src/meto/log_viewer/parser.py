"""Parser for agent reasoning JSONL log files."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path

from meto.log_viewer.models import LogEntry, ParsedLogFile, TokenUsage

logger = logging.getLogger(__name__)

# Regex pattern for token usage extraction
# Format: "Token usage - Input: 1234(567), Output: 890"
# Groups: prompt, cached, completion
TOKEN_USAGE_PATTERN = re.compile(r"Token usage - Input: (\d+)\((\d+)\), Output: (\d+)")


def extract_token_usage(message: str) -> TokenUsage | None:
    """Extract token usage from a log message string.

    Args:
        message: Log message that may contain token usage info.

    Returns:
        TokenUsage if pattern found, None otherwise.
    """
    match = TOKEN_USAGE_PATTERN.search(message)
    if match:
        return TokenUsage(
            prompt=int(match[1]),
            cached=int(match[2]),
            completion=int(match[3]),
        )
    return None


def aggregate_token_usage(entries: list[LogEntry]) -> TokenUsage:
    """Sum token usage across all entries.

    Args:
        entries: List of log entries to aggregate.

    Returns:
        TokenUsage with summed totals.
    """
    prompt = 0
    cached = 0
    completion = 0

    for entry in entries:
        usage = extract_token_usage(entry.message)
        if usage:
            prompt += usage.prompt
            cached += usage.cached
            completion += usage.completion

    return TokenUsage(prompt=prompt, cached=cached, completion=completion)


def _parse_datetime(timestamp_str: str) -> datetime:
    """Parse ISO format datetime string.

    Args:
        timestamp_str: ISO format datetime string.

    Returns:
        Parsed datetime object.

    Raises:
        ValueError: If string cannot be parsed.
    """
    return datetime.fromisoformat(timestamp_str)


def parse_log_file(file_path: Path) -> ParsedLogFile:
    """Parse a JSONL log file into structured data.

    Loads the entire file into memory and parses each line as JSON.
    Malformed lines are logged as warnings and skipped.

    Args:
        file_path: Path to the JSONL log file.

    Returns:
        ParsedLogFile with entries, aggregated token usage, and error count.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
    """
    entries: list[LogEntry] = []
    parse_errors = 0

    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
                entry = LogEntry(
                    timestamp=_parse_datetime(raw["timestamp"]),
                    level=raw["level"],
                    agent_name=raw.get("agent_name"),
                    turn=raw.get("turn"),
                    message=raw["message"],
                )
                entries.append(entry)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Skipping malformed line {line_num} in {file_path}: {e}")
                parse_errors += 1

    token_usage = aggregate_token_usage(entries)

    return ParsedLogFile(
        entries=entries,
        token_usage=token_usage,
        parse_errors=parse_errors,
    )
