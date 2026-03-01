"""FastAPI application for the log viewer API."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from meto.conf import settings
from meto.log_viewer.models import LogEntry, LogFile, TokenUsage
from meto.log_viewer.parser import (
    extract_token_usage,
    extract_token_usage_per_turn,
    parse_log_entries,
)

app = FastAPI(title="Meto Log Viewer")

# Get log directory from settings
LOG_DIR = settings.LOG_DIR


@app.get("/api/logs")
async def list_logs() -> list[LogFile]:
    """List all available log files sorted by modification date (newest first)."""
    if not LOG_DIR.exists():
        return []

    log_files: list[LogFile] = []
    for filepath in LOG_DIR.glob("*.jsonl"):
        stat = filepath.stat()
        log_files.append(
            LogFile(
                filename=filepath.name,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            )
        )

    # Sort by modification date (newest first)
    log_files.sort(key=lambda x: x.modified, reverse=True)
    return log_files


class LogResponse(TokenUsage):
    """Response model for log file content."""

    entries: list[LogEntry]
    total_tokens: TokenUsage
    tokens_per_turn: dict[str, TokenUsage]


@app.get("/api/logs/{filename}")
async def get_log(filename: str) -> dict[str, list[LogEntry] | TokenUsage | dict[str, TokenUsage]]:
    """Get parsed log entries and token usage for a specific log file.

    Args:
        filename: Name of the log file to retrieve

    Returns:
        Dictionary with 'entries', 'total_tokens', and 'tokens_per_turn' keys

    Raises:
        HTTPException: 404 if file not found
    """
    # Security: ensure filename doesn't contain path traversal
    if ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    filepath = LOG_DIR / filename

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Log file not found")

    entries = parse_log_entries(filepath)
    total_tokens = extract_token_usage(entries)
    tokens_per_turn = extract_token_usage_per_turn(entries)

    return {
        "entries": entries,
        "total_tokens": total_tokens,
        "tokens_per_turn": {str(k): v for k, v in tokens_per_turn.items()},
    }


# Serve static files (frontend) - must come after API routes
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
