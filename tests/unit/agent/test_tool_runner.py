from unittest.mock import MagicMock

from meto.agent.context import Context
from meto.agent.todo import TodoManager
from meto.agent.tool_runner import _TOOL_HANDLERS, TOOL_LOG_STRATEGY, run_tool


def test_run_tool_success():
    context = Context(todos=TodoManager(), history=[])

    def mock_handler(ctx, params):
        return f"Hello {params['name']}"

    _TOOL_HANDLERS["test_tool"] = mock_handler
    try:
        logger = MagicMock()
        result = run_tool(context, "test_tool", {"name": "World"}, logger=logger)
        assert result == "Hello World"
        logger.log_tool_selection.assert_called_with("test_tool", {"name": "World"})
        logger.log_tool_execution.assert_called_with("test_tool", "Hello World", error=False)
    finally:
        del _TOOL_HANDLERS["test_tool"]


def test_run_tool_unknown():
    context = Context(todos=TodoManager(), history=[])
    logger = MagicMock()
    result = run_tool(context, "non_existent", {}, logger=logger)
    assert "Error: Unknown tool: non_existent" in result
    logger.log_tool_execution.assert_called_with("non_existent", result, error=True)


def test_run_tool_exception():
    context = Context(todos=TodoManager(), history=[])

    def mock_handler(ctx, params):
        raise ValueError("Something went wrong")

    _TOOL_HANDLERS["error_tool"] = mock_handler
    try:
        logger = MagicMock()
        result = run_tool(context, "error_tool", {}, logger=logger)
        assert "Something went wrong" in result
        logger.log_tool_execution.assert_called_with("error_tool", result, error=True)
    finally:
        del _TOOL_HANDLERS["error_tool"]


def test_run_tool_log_strategy_invocation_only():
    context = Context(todos=TodoManager(), history=[])

    def mock_handler(ctx, params):
        return "Secret result"

    _TOOL_HANDLERS["secret_tool"] = mock_handler
    TOOL_LOG_STRATEGY["secret_tool"] = "invocation_only"
    try:
        logger = MagicMock()
        result = run_tool(context, "secret_tool", {}, logger=logger)
        assert result == "Secret result"
        logger.log_tool_selection.assert_called()
        logger.log_tool_execution.assert_not_called()
    finally:
        del _TOOL_HANDLERS["secret_tool"]
        del TOOL_LOG_STRATEGY["secret_tool"]


def test_run_tool_no_logger():
    context = Context(todos=TodoManager(), history=[])

    def mock_handler(ctx, params):
        return "No logger result"

    _TOOL_HANDLERS["no_logger_tool"] = mock_handler
    try:
        result = run_tool(context, "no_logger_tool", {})
        assert result == "No logger result"
    finally:
        del _TOOL_HANDLERS["no_logger_tool"]
