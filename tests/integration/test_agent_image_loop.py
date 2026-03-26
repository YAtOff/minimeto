from unittest.mock import MagicMock, patch

from meto.agent.agent_loop import run_agent_loop
from meto.agent.context import Context
from meto.agent.hooks import SuccessResult
from meto.agent.todo import TodoManager


def test_run_agent_loop_image_injection():
    """Verify that image-tagged tool outputs trigger a multimodal user message injection."""
    agent = MagicMock()
    agent.name = "test-agent"
    agent.has_tool.return_value = True
    agent.max_turns = 10
    agent.tool_names = ["read_file"]
    agent.tools = [{"function": {"name": "read_file"}}]
    agent.prompt = "test prompt"
    agent.features = []
    agent.model = "gpt-4"

    context = Context(todos=TodoManager(), history=[])

    mock_client = MagicMock()

    # First response: tool call to read_file
    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_image"
    mock_tool_call.type = "function"
    mock_tool_call.function.name = "read_file"
    mock_tool_call.function.arguments = '{"path": "tests/data/pixel.png"}'
    mock_tool_call.model_dump.return_value = {
        "id": "call_image",
        "type": "function",
        "function": {"name": "read_file", "arguments": '{"path": "tests/data/pixel.png"}'},
    }

    mock_response_1 = MagicMock()
    mock_response_1.choices = [MagicMock()]
    mock_response_1.choices[0].message.content = "Reading image..."
    mock_response_1.choices[0].message.tool_calls = [mock_tool_call]
    mock_response_1.usage.prompt_tokens = 10
    mock_response_1.usage.completion_tokens = 5

    # Second response: stop
    mock_response_2 = MagicMock()
    mock_response_2.choices = [MagicMock()]
    mock_response_2.choices[0].message.content = "I see the image."
    mock_response_2.choices[0].message.tool_calls = []
    mock_response_2.usage.prompt_tokens = 15
    mock_response_2.usage.completion_tokens = 10

    mock_client.chat.completions.create.side_effect = [mock_response_1, mock_response_2]

    # The tag that read_file returns for images
    image_tag = "__METO_IMAGE__:data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
        patch("meto.agent.agent_loop.pre_tool_use", return_value=SuccessResult()),
        patch("meto.agent.agent_loop.run_tool", return_value=image_tag),
        patch("meto.agent.agent_loop.post_tool_use", return_value=SuccessResult()),
        patch("meto.agent.agent_loop.registry"),
    ):
        responses = list(run_agent_loop(agent, "Read the image", context))

        assert "I see the image." in responses

        # Expected history:
        # 0: user (Read the image)
        # 1: assistant (tool call)
        # 2: tool (result with __METO_IMAGE__)
        # 3: user (multimodal injection)  <-- THIS IS WHAT WE ARE ADDING
        # 4: assistant (I see the image)

        assert len(context.history) == 5

        # Verify tool result is still there
        assert context.history[2]["role"] == "tool"
        assert context.history[2]["content"] == image_tag

        # Verify the multimodal injection message
        injection_msg = context.history[3]
        assert injection_msg["role"] == "user"
        assert isinstance(injection_msg["content"], list)
        assert injection_msg["content"][0]["type"] == "image_url"
        assert (
            injection_msg["content"][0]["image_url"]["url"]
            == "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )
