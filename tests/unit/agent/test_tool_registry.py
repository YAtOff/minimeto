import logging

import pytest

from meto.agent.tool_registry import ToolRegistration, ToolRegistry


def test_tool_registration_validation():
    def handler(_ctx, _params):
        return "result"

    schema = {"type": "function", "function": {"name": "right_name", "parameters": {}}}

    # Valid registration
    tr = ToolRegistration(name="right_name", schema=schema, description="test", handler=handler)
    assert tr.name == "right_name"

    # Mismatched name
    with pytest.raises(ValueError, match="Tool name mismatch"):
        ToolRegistration(name="wrong_name", schema=schema, description="test", handler=handler)

    # Empty name
    with pytest.raises(ValueError, match="Tool name cannot be empty"):
        ToolRegistration(name="", schema=schema, description="test", handler=handler)


def test_tool_registry_no_overwrite_by_default(caplog):
    registry = ToolRegistry()

    def handler1(_ctx, _params):
        return "result 1"

    def handler2(_ctx, _params):
        return "result 2"

    schema = {"type": "function", "function": {"name": "test_tool", "parameters": {}}}

    # Register the first tool
    registry.register_tool(
        name="test_tool", schema=schema, handler=handler1, description="First tool"
    )

    assert registry.catalog["test_tool"].description == "First tool"

    # Try to register the second tool with same name - should skip and log warning
    with caplog.at_level(logging.WARNING):
        registry.register_tool(
            name="test_tool", schema=schema, handler=handler2, description="Second tool"
        )

    # Should NOT have overwritten
    assert registry.catalog["test_tool"].description == "First tool"
    assert (
        "already registered in registry with different implementation. Skipping registration"
        in caplog.text
    )


def test_tool_registry_explicit_overwrite(caplog):
    registry = ToolRegistry()

    def handler1(_ctx, _params):
        return "result 1"

    def handler2(_ctx, _params):
        return "result 2"

    schema = {"type": "function", "function": {"name": "test_tool", "parameters": {}}}

    # Register the first tool
    registry.register_tool(
        name="test_tool", schema=schema, handler=handler1, description="First tool"
    )

    # Register with allow_overwrite=True
    with caplog.at_level(logging.WARNING):
        registry.register_tool(
            name="test_tool",
            schema=schema,
            handler=handler2,
            description="Second tool",
            allow_overwrite=True,
        )

    # Should HAVE overwritten
    assert registry.catalog["test_tool"].description == "Second tool"
    assert "Overwriting existing tool registration in registry" in caplog.text


def test_tool_registry_re_register_same_tool(caplog):
    registry = ToolRegistry()

    def handler(_ctx, _params):
        return "result"

    schema = {"type": "function", "function": {"name": "test_tool", "parameters": {}}}

    # Register the first time
    registry.register_tool(name="test_tool", schema=schema, handler=handler, description="A tool")

    # Register again with same implementation
    with caplog.at_level(logging.WARNING):
        registry.register_tool(
            name="test_tool", schema=schema, handler=handler, description="A tool"
        )

    # Should NOT have any warnings and SHOULD have the tool
    assert registry.catalog["test_tool"].description == "A tool"
    assert "already registered" not in caplog.text
    assert "Overwriting" not in caplog.text
