"""FastAPI application for log viewer API."""

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI

from meto.conf import settings
from meto.log_viewer.models import LogFile

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
