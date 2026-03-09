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


def test_execute_chat_command_help(capsys):
    session = MagicMock()
    success, output = execute_chat_command("/help", session)
    assert success is True
    assert output == ""

    captured = capsys.readouterr()
    assert "Usage:" in captured.out
    assert "help" in captured.out
    assert "quit" in captured.out
    assert "agents" in captured.out
    assert "skills" in captured.out


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


def test_compact_llm_failure_notification(capsys):
    session = MagicMock()
    # History long enough to trigger LLM summary
    session.history = [{"role": "user", "content": "Hello world" * 20}]

    with patch("openai.OpenAI") as mock_openai:
        # Mocking OpenAI to raise an exception
        mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

        success, output = execute_chat_command("/compact", session)

        # Verify it succeeded despite the LLM error (it should fallback to rule-based summary)
        assert success is True

        # Check if the error was notified to the user on stdout/stderr
        captured = capsys.readouterr()
        assert (
            "AI summarization failed: API Error" in captured.out
            or "AI summarization failed: API Error" in captured.err
        )


def test_compact_llm_success_no_notification(capsys):
    session = MagicMock()
    # History long enough to trigger LLM summary
    session.history = [{"role": "user", "content": "Hello world" * 20}]

    with patch("openai.OpenAI") as mock_openai:
        # Mocking OpenAI to return a successful summary
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "This is a successful summary."
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        success, output = execute_chat_command("/compact", session)

        assert success is True

        captured = capsys.readouterr()
        assert "AI summarization failed" not in captured.out
        assert "AI summarization failed" not in captured.err
        assert "This is a successful summary." in captured.out
