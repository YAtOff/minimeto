from unittest.mock import MagicMock, patch

import pytest

from meto.agent.context import Context
from meto.agent.tools.registry_tools import handle_search_available_tools, search_available_tools


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=Context)
    # Return a tuple as the property does
    ctx.pending_tools = []
    # Use a real list for storage in the mock if needed, but here we just need to track calls
    return ctx


def test_search_available_tools_found(mock_context):
    mock_tool = MagicMock()
    mock_tool.name = "test_tool"
    mock_tool.description = "A test tool"
    mock_tool.schema = {"function": {"name": "test_tool"}}
    mock_tool.handler = lambda x: x

    with patch("meto.agent.tools.registry_tools.registry") as mock_registry:
        mock_registry.search.return_value = [mock_tool]

        result = search_available_tools(mock_context, "test")
        assert "test_tool: A test tool" in result
        # Check that add_pending_tool was called
        mock_context.add_pending_tool.assert_called_once()
        added_tool = mock_context.add_pending_tool.call_args[0][0]
        assert added_tool.schema == mock_tool.schema


def test_search_available_tools_not_found(mock_context):
    with patch("meto.agent.tools.registry_tools.registry") as mock_registry:
        mock_registry.search.return_value = []

        result = search_available_tools(mock_context, "unknown")
        assert "No matching tools found" in result
        assert len(mock_context.pending_tools) == 0


def test_handle_search_available_tools(mock_context):
    with patch("meto.agent.tools.registry_tools.search_available_tools") as mock_search:
        mock_search.return_value = "tool list"
        params = {"query": "test", "top_k": 5}
        result = handle_search_available_tools(mock_context, params)
        assert result == "tool list"
        mock_search.assert_called_once_with(mock_context, "test", 5)
