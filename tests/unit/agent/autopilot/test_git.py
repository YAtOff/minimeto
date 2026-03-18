import subprocess
from unittest.mock import MagicMock, patch

import pytest

from meto.agent.autopilot.git import autopilot_commit
from meto.agent.autopilot.models import AutopilotTask


def test_autopilot_commit_success():
    task = AutopilotTask(id="1.1", description="Test task")

    with patch("subprocess.run") as mock_run:
        # Mock git status (has changes)
        mock_status = MagicMock()
        mock_status.stdout = " M modified_file.txt"
        mock_run.side_effect = [
            mock_status,  # git status
            MagicMock(),  # git add
            MagicMock(),  # git commit
        ]

        assert autopilot_commit(task) is True

        assert mock_run.call_count == 3
        mock_run.assert_any_call(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )
        mock_run.assert_any_call(["git", "add", "."], check=True)
        mock_run.assert_any_call(
            ["git", "commit", "-m", "autopilot: completed task 1.1 - Test task"], check=True
        )


def test_autopilot_commit_no_changes():
    task = AutopilotTask(id="1.1", description="Test task")

    with patch("subprocess.run") as mock_run:
        # Mock git status (no changes)
        mock_status = MagicMock()
        mock_status.stdout = ""
        mock_run.return_value = mock_status

        assert autopilot_commit(task) is True

        assert mock_run.call_count == 1
        mock_run.assert_called_once_with(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        )


def test_autopilot_commit_failure():
    task = AutopilotTask(id="1.1", description="Test task")

    with patch("subprocess.run") as mock_run:
        # Mock git status (has changes)
        mock_status = MagicMock()
        mock_status.stdout = " M modified_file.txt"

        # Mock git commit failure
        error = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "commit", "-m", "..."],
            stderr="error: failed to push some refs...",
        )

        mock_run.side_effect = [
            mock_status,  # git status
            MagicMock(),  # git add
            error,  # git commit fails
        ]

        with pytest.raises(RuntimeError) as excinfo:
            autopilot_commit(task)

        assert "Git commit failed" in str(excinfo.value)
        assert "exit code 1" in str(excinfo.value)
        assert "error: failed to push some refs" in str(excinfo.value)
