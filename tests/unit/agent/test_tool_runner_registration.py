import logging

from meto.agent.tool_runner import _TOOL_HANDLERS, register_tool_handler


def test_register_tool_handler_overwrite_warning(caplog):
    # Setup: ensure a tool exists
    def original_handler(_ctx, _params):
        return "original"

    def new_handler(_ctx, _params):
        return "new"

    _TOOL_HANDLERS["test_warning_tool"] = original_handler

    try:
        # Re-registering SAME handler should NOT warn
        with caplog.at_level(logging.WARNING):
            register_tool_handler("test_warning_tool", original_handler)
        assert "Overwriting existing tool handler" not in caplog.text

        caplog.clear()

        # Re-registering DIFFERENT handler SHOULD warn
        with caplog.at_level(logging.WARNING):
            register_tool_handler("test_warning_tool", new_handler)
        assert (
            "Overwriting existing tool handler with a different one: test_warning_tool"
            in caplog.text
        )
        assert _TOOL_HANDLERS["test_warning_tool"] == new_handler

    finally:
        if "test_warning_tool" in _TOOL_HANDLERS:
            del _TOOL_HANDLERS["test_warning_tool"]
