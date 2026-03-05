"""FastAPI application for log viewer API."""

from __future__ import annotations

import logging
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles

from meto.conf import settings
from meto.log_viewer.models import LogFile, ParsedLogFile
from meto.log_viewer.parser import parse_log_file
from meto.log_viewer.security import safe_join_path

logger = logging.getLogger(__name__)

app = FastAPI(title="Meto Log Viewer API")


@app.get("/api/logs", response_model=list[LogFile])
async def list_logs() -> list[LogFile]:
    """List all log files sorted by modification date (newest first)."""
    log_dir: Path = settings.LOG_DIR

    # Return empty list if directory doesn't exist
    if not log_dir.exists():
        return []

    # Collect log file metadata
    log_files: list[LogFile] = []
    for file_path in log_dir.iterdir():
        if file_path.is_file():
            stat = file_path.stat()
            log_files.append(
                LogFile(
                    filename=file_path.name,
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                )
            )

    # Sort by modification date, newest first
    log_files.sort(key=lambda x: x.modified, reverse=True)

    return log_files


@app.get("/api/logs/{filename}", response_model=ParsedLogFile)
async def get_log(filename: str) -> ParsedLogFile:
    """Retrieve and parse a single log file by filename."""
    log_dir: Path = settings.LOG_DIR

    # Safely construct the full path (prevents traversal attacks)
    file_path = safe_join_path(log_dir, filename)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid filename: {filename}",
        )

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log file not found: {filename}",
        )

    # Parse the log file
    try:
        return parse_log_file(file_path)
    except PermissionError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Permission denied reading file: {filename}",
        ) from None
    except Exception as e:
        logger.error(f"Unexpected error parsing {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while parsing log file",
        ) from None


def run_server(
    host: str = "localhost",
    port: int = 8000,
    open_browser: bool = True,
) -> None:
    """Start the log viewer server.

    Args:
        host: Host to bind the server to.
        port: Port to bind the server to.
        open_browser: Whether to auto-open the browser.
    """

    def open_browser_delayed() -> None:
        """Open browser after a short delay to ensure server is ready."""
        if open_browser:
            time.sleep(1.5)  # Wait for server to start
            webbrowser.open(f"http://{host}:{port}")

    if open_browser:
        browser_thread = threading.Thread(target=open_browser_delayed, daemon=True)
        browser_thread.start()

    try:
        uvicorn.run(
            "meto.log_viewer.app:app",
            host=host,
            port=port,
            reload=False,
            log_level="warning",
        )
    except OSError as e:
        if "Address already in use" in str(e) or e.errno == 48:
            print(f"Error: Port {port} is already in use.")
            print(f"Try: meto logs --serve --port {port + 1}")
            raise SystemExit(1) from None
        raise


# Static files mount - must be AFTER all API routes
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
