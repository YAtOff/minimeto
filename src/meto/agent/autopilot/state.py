from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from meto.agent.autopilot.models import AutopilotSession
from meto.conf import settings

logger = logging.getLogger(__name__)


class AutopilotState:
    """Manages persistent storage for autopilot sessions."""

    state_file: Path

    def __init__(self, state_file: str | Path | None = None) -> None:
        if state_file is None:
            state_file = settings.SESSION_DIR / ".autopilot_state.json"
        self.state_file = Path(state_file)
        self.session: AutopilotSession | None = None

    def load(self) -> AutopilotSession | None:
        """Load session state from disk."""
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, encoding="utf-8") as f:
                data = json.load(f)
                self.session = AutopilotSession.model_validate(data)
                return self.session
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                f"Failed to load autopilot state from {self.state_file}: {e}. "
                f"File will be backed up and a new session started.",
                exc_info=True,
            )
            # Backup corrupted file for recovery
            backup_path = self.state_file.with_suffix(".corrupted")
            try:
                import shutil

                shutil.copy(self.state_file, backup_path)
                logger.info(f"Corrupted state backed up to {backup_path}")
            except OSError as backup_error:
                logger.error(f"Failed to backup corrupted state file: {backup_error}")

            # Notify user
            from rich.console import Console

            console = Console()
            console.print(
                f"\n[bold red]⚠️ Warning:[/] Autopilot state file is corrupted.\n"
                f"Backed up to: {backup_path}\n"
                f"Starting a new session. You can manually recover data from the backup if needed.\n"
            )
            return None

    def save(self, session: AutopilotSession | None = None) -> None:
        """Save session state to disk atomically."""
        if session:
            self.session = session

        if not self.session:
            return

        temp_file = self.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(self.session.model_dump_json(indent=2))
            os.replace(temp_file, self.state_file)
        except OSError as e:
            logger.error(
                f"Failed to save autopilot state to {self.state_file}: {e}. "
                f"Session state may be lost on crash.",
                exc_info=True,
            )
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError as unlink_error:
                    logger.error(f"Failed to cleanup temp file {temp_file}: {unlink_error}")

            # Notify user immediately
            from rich.console import Console

            console = Console()
            console.print(
                f"\n[bold red]⚠️ Warning:[/] Failed to save autopilot state: {e}\n"
                f"Your progress may not persist if the session crashes.\n"
                f"Check disk space and file permissions.\n"
            )

    def delete(self) -> None:
        """Remove the state file from disk."""
        if self.state_file.exists():
            try:
                self.state_file.unlink()
                logger.info(f"Deleted autopilot state file: {self.state_file}")
            except OSError as e:
                logger.error(f"Failed to delete state file {self.state_file}: {e}", exc_info=True)
                raise RuntimeError(f"Failed to delete state file: {e}") from e
        self.session = None

    @classmethod
    def exists(cls, state_file: str | Path | None = None) -> bool:
        """Check if a state file exists."""
        if state_file is None:
            state_file = settings.SESSION_DIR / ".autopilot_state.json"
        return Path(state_file).exists()
