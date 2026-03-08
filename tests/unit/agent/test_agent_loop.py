from unittest.mock import MagicMock, patch

import pytest

from meto.agent.agent_loop import run_agent_loop
from meto.agent.context import Context
from meto.agent.exceptions import MaxStepsExceededError
from meto.agent.hooks import ErrorResult, InjectedResult, SuccessResult
from meto.agent.todo import TodoManager


def test_run_agent_loop_success():
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]
    agent.tools = [{"function": {"name": "test_tool"}}]

    context = Context(todos=TodoManager(), history=[])

    mock_client = MagicMock()

    # First response: tool call
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_1"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = '{"arg": "val"}'
    mock_tool_call.model_dump.return_value = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "test_tool", "arguments": '{"arg": "val"}'},
    }

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.content = "Thinking..."
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
    mock_response_1.usage.prompt_tokens = 10
    mock_response_1.usage.completion_tokens = 5

    # Second response: stop
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.content = "Done!"
    mock_response_2.choices[0].message.tool_calls = []
    mock_response_2.usage.prompt_tokens = 15
    mock_response_2.usage.completion_tokens = 10

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.pre_tool_use", return_value=SuccessResult()),
        patch("meto.agent.agent_loop.run_tool", return_value="Tool output"),
        patch("meto.agent.agent_loop.post_tool_use", return_value=SuccessResult()),
        patch("meto.agent.agent_loop.registry"),
    ):
        responses = list(run_agent_loop(agent, "User prompt", context))

        assert responses == ["Thinking...", "Done!"]
        assert len(context.history) == 4  # user, assistant (call), tool, assistant (final)
        assert context.history[2]["role"] == "tool"
        assert context.history[2]["content"] == "Tool output"


def test_run_agent_loop_unknown_tool():
    agent = MagicMock()
    agent.has_tool.return_value = False  # Tool not allowed for this agent
    agent.max_turns = 10
    agent.tool_names = []

    context = Context(todos=TodoManager(), history=[])
    mock_client = MagicMock()

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_unknown"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "unknown_tool"
    mock_tool_call.function.arguments = "{}"
    mock_tool_call.model_dump.return_value = {
        "id": "call_unknown",
        "function": {"name": "unknown_tool"},
    }

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.content = ""
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.content = "Stop"
    mock_response_2.choices[0].message.tool_calls = []

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.registry"),
    ):
        list(run_agent_loop(agent, "Hi", context))

        tool_msg = next(m for m in context.history if m["role"] == "tool")
        assert "Unknown tool" in tool_msg["content"]


def test_run_agent_loop_pre_tool_error():
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]

    context = Context(todos=TodoManager(), history=[])
    mock_client = MagicMock()

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_error"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = "{}"
    mock_tool_call.model_dump.return_value = {"id": "call_error", "function": {"name": "test_tool"}}

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.tool_calls = []

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.pre_tool_use", return_value=ErrorResult(error="Blocked!")),
        patch("meto.agent.agent_loop.registry"),
    ):
        list(run_agent_loop(agent, "Hi", context))

        tool_msg = next(m for m in context.history if m["role"] == "tool")
        assert "Blocked!" in tool_msg["content"]


def test_run_agent_loop_pre_tool_injected():
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]

    context = Context(todos=TodoManager(), history=[])
    mock_client = MagicMock()

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_inject"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = "{}"
    mock_tool_call.model_dump.return_value = {
        "id": "call_inject",
        "function": {"name": "test_tool"},
    }

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]

    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.tool_calls = []

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch(
            "meto.agent.agent_loop.pre_tool_use",
            return_value=InjectedResult(injected_content="New rules"),
        ),
        patch("meto.agent.agent_loop.registry"),
    ):
        list(run_agent_loop(agent, "Hi", context))

        system_msg = next(m for m in context.history if m["role"] == "system")
        assert system_msg["content"] == "New rules"


def test_run_agent_loop_max_turns():
    agent = MagicMock()
    agent.max_turns = 1
    agent.tool_names = []

    context = Context(todos=TodoManager(), history=[])
    mock_client = MagicMock()

    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [
        MagicMock(type="function", function=MagicMock(name="some_tool", arguments="{}"))
    ]

    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.registry"),
    ):
        with pytest.raises(MaxStepsExceededError):
            list(run_agent_loop(agent, "Hi", context))


def test_run_agent_loop_pending_tools():
    agent = MagicMock()
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["test_tool"]
    agent.tools = [{"function": {"name": "test_tool"}}]

    context = Context(todos=TodoManager(), history=[])

    # Simulate a tool adding a pending tool
    pending_tool = MagicMock()
    pending_tool.schema = {"function": {"name": "new_tool"}}
    pending_tool.handler = MagicMock()
    context.pending_tools.append(pending_tool)

    mock_client = MagicMock()

    # First response: call test_tool
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_1"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = "{}"
    mock_tool_call.model_dump.return_value = {"id": "call_1", "function": {"name": "test_tool"}}

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]

    # Second response: stop
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.tool_calls = []

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.run_tool", return_value="done"),
        patch("meto.agent.agent_loop.register_tool_handler") as mock_register,
        patch("meto.agent.agent_loop.registry"),
    ):
        list(run_agent_loop(agent, "Hi", context))

        # Verify new tool was added to agent and registered
        assert any(t["function"]["name"] == "new_tool" for t in agent.tools)
        mock_register.assert_any_call("new_tool", pending_tool.handler)
        assert len(context.pending_tools) == 0


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
        patch("meto.agent.agent_loop.registry"),
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
        patch("meto.agent.agent_loop.registry"),
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
