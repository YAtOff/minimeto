"""Parser for agent reasoning JSONL log files."""

import json
import re
import warnings
from pathlib import Path

from meto.log_viewer.models import LogEntry, TokenUsage


def parse_log_entries(filepath: Path) -> list[LogEntry]:
    """Parse a JSONL log file and return a list of LogEntry objects.

    Args:
        filepath: Path to the JSONL log file

    Returns:
        List of LogEntry objects parsed from the file
    """
    entries: list[LogEntry] = []

    with open(filepath, encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                entry = LogEntry(
                    timestamp=data["timestamp"],
                    level=data["level"],
                    agent_name=data.get("agent_name", "unknown"),
                    turn=data.get("turn"),
                    message=data["message"],
                )
                entries.append(entry)
            except (json.JSONDecodeError, KeyError) as e:
                warnings.warn(f"Skipping malformed line {line_num}: {e}", stacklevel=2)

    return entries


def extract_token_usage(entries: list[LogEntry]) -> TokenUsage:
    """Extract aggregated token usage from log entries.

    Looks for messages like: "Token usage - Input: 2858(0), Output: 144"

    Args:
        entries: List of LogEntry objects to scan

    Returns:
        TokenUsage with aggregated prompt, cached, and completion counts
    """
    total_prompt = 0
    total_cached = 0
    total_completion = 0

    # Pattern matches: "Token usage - Input: 2858(0), Output: 144"
    pattern = re.compile(r"Token usage - Input: (\d+)\((\d+)\), Output: (\d+)")

    for entry in entries:
        match = pattern.search(entry.message)
        if match:
            total_prompt += int(match.group(1))
            total_cached += int(match.group(2))
            total_completion += int(match.group(3))

    return TokenUsage(
        prompt=total_prompt,
        cached=total_cached,
        completion=total_completion,
    )


def extract_token_usage_per_turn(entries: list[LogEntry]) -> dict[int | str, TokenUsage]:
    """Extract token usage per turn from log entries.

    Token usage messages are logged at the end of each turn, so we associate
    them with the turn number of that entry.

    Args:
        entries: List of LogEntry objects to scan

    Returns:
        Dictionary mapping turn numbers to TokenUsage objects
    """
    per_turn: dict[int | str, TokenUsage] = {}

    # Pattern matches: "Token usage - Input: 2858(0), Output: 144"
    pattern = re.compile(r"Token usage - Input: (\d+)\((\d+)\), Output: (\d+)")

    for entry in entries:
        match = pattern.search(entry.message)
        if match:
            # Use the entry's turn number (or 'pre' for pre-turn entries)
            turn_key = entry.turn if entry.turn is not None else "pre"

            if turn_key not in per_turn:
                per_turn[turn_key] = TokenUsage(prompt=0, cached=0, completion=0)

            current = per_turn[turn_key]
            per_turn[turn_key] = TokenUsage(
                prompt=current.prompt + int(match.group(1)),
                cached=current.cached + int(match.group(2)),
                completion=current.completion + int(match.group(3)),
            )

    return per_turn
