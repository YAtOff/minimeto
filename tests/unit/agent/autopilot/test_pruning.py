from unittest.mock import MagicMock, patch

from meto.agent.autopilot.pruning import summarize_tool_output
from meto.agent.exceptions import LLMError


@patch("meto.agent.autopilot.pruning.get_client")
def test_summarize_tool_output_llm_error_fallback(mock_get_client, caplog):
    """Test that generic Exception during summarization falls back to truncation and logs the error."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    # Mock generic Exception
    mock_client.chat.completions.create.side_effect = Exception("LLM connection failed")

    tool_name = "test_tool"
    output = "a" * 3000
    max_chars = 2000

    with caplog.at_level("ERROR"):
        # We expect it to fallback to truncation
        result = summarize_tool_output(tool_name, output, max_chars)

    assert "[Output truncated from 3000 chars due to unexpected error]" in result
    assert "LLM connection failed" in caplog.text
    assert f"tool '{tool_name}'" in caplog.text
    assert len(result) <= max_chars + 100  # Allow some buffer for the prefix
    assert "..." in result


@patch("meto.agent.autopilot.pruning.get_client")
def test_summarize_tool_output_llmerror_fallback(mock_get_client, caplog):
    """Test that LLMError during summarization falls back to truncation and logs the error."""
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    # Mock LLMError
    mock_client.chat.completions.create.side_effect = LLMError("LiteLLM API Error")

    tool_name = "test_tool"
    output = "a" * 3000
    max_chars = 2000

    with caplog.at_level("ERROR"):
        # We expect it to fallback to truncation
        result = summarize_tool_output(tool_name, output, max_chars)

    assert "[Output truncated from 3000 chars due to unexpected error]" in result
    assert "LiteLLM API Error" in caplog.text
    assert f"tool '{tool_name}'" in caplog.text
    assert len(result) <= max_chars + 100  # Allow some buffer for the prefix
    assert "..." in result
