from unittest.mock import MagicMock, patch

import pytest

from meto.agent.context import Context
from meto.agent.tools.interactive_tools import ask_user_question, handle_ask_user_question


@pytest.fixture
def mock_context():
    return MagicMock(spec=Context)


def test_ask_user_question_success(mock_context):
    with patch("meto.agent.tools.interactive_tools.PromptSession") as mock_session_class:
        mock_session = mock_session_class.return_value
        mock_session.prompt.return_value = "user answer"

        with patch("meto.agent.tools.interactive_tools.Console"):
            result = ask_user_question(mock_context, "What is your name?")
            assert result == "user answer"
            mock_session.prompt.assert_called_once_with("")


def test_ask_user_question_cancelled(mock_context):
    with patch("meto.agent.tools.interactive_tools.PromptSession") as mock_session_class:
        mock_session = mock_session_class.return_value
        mock_session.prompt.side_effect = KeyboardInterrupt()

        with patch("meto.agent.tools.interactive_tools.Console"):
            result = ask_user_question(mock_context, "Cancel me?")
            assert result == "(user cancelled input)"


def test_handle_ask_user_question(mock_context):
    with patch("meto.agent.tools.interactive_tools.ask_user_question") as mock_ask:
        mock_ask.return_value = "answer"
        params = {"question": "How are you?"}
        result = handle_ask_user_question(mock_context, params)
        assert result == "answer"
        mock_ask.assert_called_once_with(mock_context, "How are you?")
