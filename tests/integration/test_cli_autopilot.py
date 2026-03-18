from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from meto.agent.exceptions import AgentInterrupted
from meto.cli import app

runner = CliRunner()


def test_autopilot_keyboard_interrupt():
    """Test that KeyboardInterrupt in autopilot is handled and exits with 130."""
    goal_text = "test goal"

    with (
        patch("meto.cli.Session.new") as mock_session_new,
        patch("meto.cli.run_autopilot_loop") as mock_run_loop,
        patch("meto.cli.TodoManager"),
        patch("meto.cli.Context"),
    ):
        mock_session = MagicMock()
        mock_session_new.return_value = mock_session

        # Simulate KeyboardInterrupt during the loop
        mock_run_loop.side_effect = KeyboardInterrupt()

        # Run CLI with --autopilot and --prompt
        result = runner.invoke(app, ["--autopilot", "--prompt", goal_text])

        assert result.exit_code == 130
        assert "[Autopilot interrupted]" in result.stderr


def test_autopilot_agent_interrupted():
    """Test that AgentInterrupted in autopilot is handled and exits with 130."""
    goal_text = "test goal"

    with (
        patch("meto.cli.Session.new") as mock_session_new,
        patch("meto.cli.run_autopilot_loop") as mock_run_loop,
        patch("meto.cli.TodoManager"),
        patch("meto.cli.Context"),
    ):
        mock_session = MagicMock()
        mock_session_new.return_value = mock_session

        # Simulate AgentInterrupted during the loop
        mock_run_loop.side_effect = AgentInterrupted("User interrupted")

        # Run CLI with --autopilot and --prompt
        result = runner.invoke(app, ["--autopilot", "--prompt", goal_text])

        assert result.exit_code == 130
        assert "[Autopilot interrupted]" in result.stderr


def test_autopilot_general_exception():
    """Test that general Exception in autopilot is handled and exits with 1."""
    goal_text = "test goal"

    with (
        patch("meto.cli.Session.new") as mock_session_new,
        patch("meto.cli.run_autopilot_loop") as mock_run_loop,
        patch("meto.cli.TodoManager"),
        patch("meto.cli.Context"),
    ):
        mock_session = MagicMock()
        mock_session_new.return_value = mock_session

        # Simulate general Exception during the loop
        mock_run_loop.side_effect = Exception("Something went wrong")

        # Run CLI with --autopilot and --prompt
        result = runner.invoke(app, ["--autopilot", "--prompt", goal_text])

        assert result.exit_code == 1
        assert "[Error] Autopilot failed: Something went wrong" in result.stderr


def test_oneshot_keyboard_interrupt():
    """Test that KeyboardInterrupt in one-shot mode is handled and exits with 130."""
    prompt_text = "test prompt"

    with (
        patch("meto.cli.Session.new") as mock_session_new,
        patch("meto.cli._run_single_prompt") as mock_run_single,
    ):
        mock_session = MagicMock()
        mock_session_new.return_value = mock_session

        # Simulate KeyboardInterrupt during the execution
        mock_run_single.side_effect = KeyboardInterrupt()

        # Run CLI with --one-shot and --prompt
        result = runner.invoke(app, ["--one-shot", "--prompt", prompt_text])

        assert result.exit_code == 130
        assert "[Agent interrupted]" in result.stderr
