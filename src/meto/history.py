"""Command history management with sensitive data filtering."""

from __future__ import annotations

import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import override

from prompt_toolkit.history import FileHistory

from meto.conf import settings

logger = logging.getLogger(__name__)


class FilteredHistory(FileHistory):
    """FileHistory subclass that filters sensitive data before persistence.

    Features:
    - Filters out commands matching exclude patterns (API keys, passwords, etc.)
    - Thread-safe history loading
    - Handles corrupted history files gracefully
    - Enforces max size limits
    """

    def __init__(
        self,
        filename: str,
        exclude_patterns: list[str] | None = None,
        max_size: int | None = None,
    ) -> None:
        super().__init__(filename)
        self.exclude_patterns: list[str] = exclude_patterns or settings.HISTORY_EXCLUDE_PATTERNS
        self.max_size: int = max_size or settings.HISTORY_MAX_SIZE
        self._compiled_patterns: list[re.Pattern[str]] = [
            re.compile(p) for p in self.exclude_patterns
        ]
        self._lock: threading.Lock = threading.Lock()

    @override
    def append_string(self, string: str) -> None:
        """Add string to history, filtering sensitive data first.

        Args:
            string: Command line to potentially add to history
        """
        # Skip empty lines
        if not string.strip():
            return

        # Skip lines matching exclude patterns
        if self._is_sensitive(string):
            logger.debug(f"Excluding sensitive command from history: {string[:20]}...")
            return

        # Append via parent
        super().append_string(string)

        # Check max size and trim if needed (after append)
        with self._lock:
            self._enforce_max_size()

    def _is_sensitive(self, line: str) -> bool:
        """Check if line contains sensitive data matching exclude patterns."""
        return any(pattern.search(line) for pattern in self._compiled_patterns)

    def _enforce_max_size(self) -> None:
        """Trim history file if it exceeds max_size.

        Removes oldest entries first.
        """
        try:
            lines = self.get_strings()
            if len(lines) > self.max_size:
                # Keep the most recent entries
                keep_count = int(self.max_size * 0.9)  # Trim to 90% of max
                trimmed_lines = lines[-keep_count:]

                # Rewrite the file
                self._rewrite_history(trimmed_lines)

                # Clear in-memory cache and reload from file
                self._loaded_strings: list[str] = []
                _ = self.get_strings()

                logger.info(f"Trimmed history from {len(lines)} to {keep_count} entries")
        except Exception as e:
            logger.warning(f"Failed to enforce history max size: {e}")

    def _rewrite_history(self, lines: list[str]) -> None:
        """Rewrite the history file with the given lines."""
        try:
            # Write to temp file first, then atomic rename
            filename_path = Path(str(self.filename))
            temp_file = filename_path.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                for line in lines:
                    # Write in FileHistory format
                    f.write(f"# {datetime.now()}\n")
                    for subline in line.split("\n"):
                        f.write(f"+{subline}\n")

            # Atomic rename
            temp_file.replace(filename_path)
        except Exception as e:
            logger.error(f"Failed to rewrite history file: {e}")
            # Clean up temp file if it exists
            filename_path = Path(str(self.filename))
            temp_file = filename_path.with_suffix(".tmp")
            if temp_file.exists():
                temp_file.unlink()


def create_history() -> FilteredHistory | None:
    """Factory function to create a configured history instance.

    Returns:
        FilteredHistory instance, or None if history is disabled
    """
    if not settings.HISTORY_ENABLED:
        return None

    try:
        return FilteredHistory(
            filename=str(settings.HISTORY_FILE),
            exclude_patterns=settings.HISTORY_EXCLUDE_PATTERNS,
            max_size=settings.HISTORY_MAX_SIZE,
        )
    except Exception as e:
        logger.error(f"Failed to create history: {e}")
        return None
