from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from meto.cli import app

runner = CliRunner()


def test_cli_yolo_flag_creates_yolo_session():
    """Test that --yolo flag creates session with yolo=True."""
    # Mock Session.new to capture the yolo parameter
    with patch("meto.cli.Session.new") as mock_new:
        mock_new.return_value = MagicMock()

        # Mock _run_single_prompt to avoid actual execution
        with patch("meto.cli._run_single_prompt"):
            # Run CLI with --yolo and --one-shot
            result = runner.invoke(app, ["--yolo", "--one-shot", "--prompt", "test"])

            # Verify Session.new was called with yolo=True
            mock_new.assert_called_once_with(yolo=True)
            assert result.exit_code == 0


def test_cli_no_yolo_flag_creates_normal_session():
    """Test that missing --yolo flag creates session with yolo=False."""
    with patch("meto.cli.Session.new") as mock_new:
        mock_new.return_value = MagicMock()

        with patch("meto.cli._run_single_prompt"):
            result = runner.invoke(app, ["--one-shot", "--prompt", "test"])

            # Verify Session.new was called with yolo=False
            mock_new.assert_called_once_with(yolo=False)
            assert result.exit_code == 0


def test_cli_yolo_flag_with_existing_session():
    """Test that --yolo flag is passed to Session.load."""
    session_id = "20240310_123456-abc123"

    with patch("meto.cli.Session.load") as mock_load:
        mock_load.return_value = MagicMock()

        with patch("meto.cli._run_single_prompt"):
            result = runner.invoke(
                app, ["--session", session_id, "--yolo", "--one-shot", "--prompt", "test"]
            )

            # Verify Session.load was called with yolo=True
            mock_load.assert_called_once_with(session_id, yolo=True)
            assert result.exit_code == 0
