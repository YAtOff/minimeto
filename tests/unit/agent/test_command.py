from unittest.mock import MagicMock, patch

import pytest
from typer import Exit

from meto.agent.command import NewSessionException, execute_chat_command


def test_execute_chat_command_invalid():
    session = MagicMock()
    success, output = execute_chat_command("not a command", session)
    assert success is False
    assert output == ""


def test_execute_chat_command_unknown():
    session = MagicMock()
    success, output = execute_chat_command("/unknown", session)
    assert success is False
    assert "Unknown command" in output


def test_execute_chat_command_help():
    session = MagicMock()
    with patch("meto.agent.command.chat_commands.get_help") as mock_get_help:
        mock_get_help.return_value = "Help text"
        success, output = execute_chat_command("/help", session)
        assert success is True
        assert (
            output == ""
        )  # help echos to stdout, so execute_chat_command returns empty string on success


def test_execute_chat_command_new():
    session = MagicMock()
    with pytest.raises(NewSessionException):
        execute_chat_command("/new", session)


def test_execute_chat_command_quit():
    session = MagicMock()
    with pytest.raises(Exit):
        execute_chat_command("/quit", session)


def test_execute_chat_command_exit_alias():
    session = MagicMock()
    with pytest.raises(Exit):
        execute_chat_command("/exit", session)


def test_execute_chat_command_context():
    session = MagicMock()
    session.history = []
    with patch("meto.agent.command.format_context_summary") as mock_format:
        success, output = execute_chat_command("/context", session)
        assert success is True
        mock_format.assert_called_with([])


def test_execute_chat_command_export():
    session = MagicMock()
    session.history = []
    with patch("meto.agent.command.dump_agent_context") as mock_dump:
        mock_dump.return_value = "Context content"
        success, output = execute_chat_command("/export", session)
        assert success is True
        mock_dump.assert_called()
