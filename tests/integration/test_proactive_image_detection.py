import os
from unittest.mock import MagicMock, patch

from meto.agent.agent_loop import run_agent_loop
from meto.agent.context import Context
from meto.agent.todo import TodoManager


def test_proactive_image_detection():
    """Verify that images in the initial prompt are proactively attached as multimodal messages."""
    agent = MagicMock()
    agent.name = "test-agent"
    agent.max_turns = 10
    agent.tool_names = []
    agent.tools = []
    agent.prompt = "test prompt"
    agent.features = []
    agent.model = "gpt-4"
    agent.has_tool.return_value = False

    context = Context(todos=TodoManager(), history=[])

    mock_client = MagicMock()

    # Mock response from LLM
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "I see the image in your prompt."
    mock_response.choices[0].message.tool_calls = []
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    mock_client.chat.completions.create.return_value = mock_response

    # Use an existing image from tests/data/pixel.png
    # Ensure we use the absolute path as the prompt scanner resolves paths
    image_path = os.path.abspath("tests/data/pixel.png")
    prompt = f"Analyze this image: {image_path}"

    with (
        patch("meto.agent.agent_loop.get_client", return_value=mock_client),
        patch("meto.agent.agent_loop.build_system_prompt", return_value="System prompt"),
        patch("meto.agent.agent_loop.ReasoningLogger"),
    ):
        responses = list(run_agent_loop(agent, prompt, context))

        assert "I see the image in your prompt." in responses

        # Verify that the first message in history is multimodal
        # context.history[0] should be the user message
        assert len(context.history) > 0
        user_msg = context.history[0]
        assert user_msg["role"] == "user"

        # Current behavior (before fix): user_msg["content"] == prompt (string)
        # Desired behavior (after fix): user_msg["content"] is a list
        assert isinstance(user_msg["content"], list), (
            f"Expected list content, got {type(user_msg['content'])}"
        )

        # Verify text content
        assert any(
            item["type"] == "text" and prompt in item["text"] for item in user_msg["content"]
        )

        # Verify image content
        image_items = [item for item in user_msg["content"] if item["type"] == "image_url"]
        assert len(image_items) > 0
        assert image_items[0]["image_url"]["url"].startswith("data:image/png;base64,")
