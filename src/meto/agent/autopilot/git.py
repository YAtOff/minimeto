from __future__ import annotations

import logging
import subprocess

from meto.agent.autopilot.models import AutopilotTask

logger = logging.getLogger(__name__)


def autopilot_commit(task: AutopilotTask) -> bool:
    """Create a git commit for the completed task.

    Args:
        task: The completed autopilot task.

    Returns:
        True if commit was successful or no changes to commit.

    Raises:
        RuntimeError: If the git command fails.
    """
    message = f"autopilot: completed task {task.id} - {task.description}"

    try:
        # Check if there are changes to commit
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        if not status.stdout.strip():
            logger.info("No changes to commit for task %s", task.id)
            return True

        # Stage and commit
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        logger.info("Committed task %s: %s", task.id, message)
        return True
    except subprocess.CalledProcessError as e:
        error_details = f"Command '{e.cmd}' failed with exit code {e.returncode}"
        if e.stderr:
            error_details += f": {e.stderr}"
        logger.error(f"Failed to commit task {task.id}: {error_details}", exc_info=True)
        raise RuntimeError(f"Git commit failed: {error_details}") from e
