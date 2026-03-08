from unittest.mock import MagicMock, patch

from meto.agent.agent_loop import run_agent_loop
from meto.agent.context import Context
from meto.agent.todo import TodoManager


def test_run_agent_loop_json_parsing_failure_reported():
    # Setup
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]

    context = Context(todos=TodoManager(), history=[])

    # Mock LLM response with invalid JSON arguments
    mock_client = MagicMock()

    # Mock tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_123"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = "invalid json {"  # Missing closing brace

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I will call a tool"
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.choices[0].finish_reason = "tool_calls"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    # Second response to stop the loop (no tool calls)
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.content = "Done"
    mock_response_2.choices[0].message.tool_calls = []
    mock_response_2.choices[0].finish_reason = "stop"
    mock_response_2.usage.prompt_tokens = 10
    mock_response_2.usage.completion_tokens = 5

    mock_client.chat.completions.create.side_effect = [mock_response, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.run_tool") as mock_run_tool,
    ):
        # Run the loop
        list(run_agent_loop(agent, "Hello", context))

        # Verify fix: run_tool should NOT be called
        mock_run_tool.assert_not_called()

        # Verify error is in history
        tool_results = [h for h in context.history if h.get("role") == "tool"]
        assert len(tool_results) == 1
        assert tool_results[0]["tool_call_id"] == "call_123"
        assert "Error: Could not parse tool arguments" in tool_results[0]["content"]


def test_run_agent_loop_non_dict_arguments_reported():
    # Setup
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]

    context = Context(todos=TodoManager(), history=[])

    # Mock LLM response with list arguments instead of dict
    mock_client = MagicMock()

    # Mock tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_456"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = "[1, 2, 3]"  # Valid JSON but not a dict

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I will call a tool"
    mock_response.choices[0].message.tool_calls = [mock_tool_call]
    mock_response.choices[0].finish_reason = "tool_calls"
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    # Second response to stop the loop (no tool calls)
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.content = "Done"
    mock_response_2.choices[0].message.tool_calls = []
    mock_response_2.choices[0].finish_reason = "stop"
    mock_response_2.usage.prompt_tokens = 10
    mock_response_2.usage.completion_tokens = 5

    mock_client.chat.completions.create.side_effect = [mock_response, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.run_tool") as mock_run_tool,
    ):
        # Run the loop
        list(run_agent_loop(agent, "Hello", context))

        # This will currently FAIL if it silently falls back to {}
        mock_run_tool.assert_not_called()

        # Verify error is in history
        tool_results = [h for h in context.history if h.get("role") == "tool"]
        assert len(tool_results) == 1
        assert tool_results[0]["tool_call_id"] == "call_456"
        assert "Error: Tool arguments must be a dictionary" in tool_results[0]["content"]
