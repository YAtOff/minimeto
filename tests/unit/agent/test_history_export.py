import json

from meto.agent.history_export import dump_agent_context


def test_dump_agent_context_markdown_with_invalid_json():
    history = [
        {
            "role": "assistant",
            "content": "Calling tool",
            "tool_calls": [
                {"function": {"name": "invalid_tool", "arguments": '{"key": "value", invalid}'}}
            ],
        }
    ]
    output = dump_agent_context(history, output_format="markdown")
    assert "invalid_tool" in output
    assert '{"key": "value", invalid}' in output


def test_dump_agent_context_text_with_invalid_json():
    history = [
        {
            "role": "assistant",
            "content": "Calling tool",
            "tool_calls": [
                {"function": {"name": "invalid_tool", "arguments": '{"key": "value", invalid}'}}
            ],
        }
    ]
    output = dump_agent_context(history, output_format="text")
    assert "invalid_tool" in output
    assert 'Args: {"key": "value", invalid}' in output


def test_dump_agent_context_json_valid():
    history = [{"role": "user", "content": "hello"}]
    output = dump_agent_context(history, output_format="json")
    parsed = json.loads(output)
    assert parsed == history


def test_dump_agent_context_markdown_valid_json():
    history = [
        {
            "role": "assistant",
            "content": "Calling tool",
            "tool_calls": [{"function": {"name": "valid_tool", "arguments": '{"key": "value"}'}}],
        }
    ]
    output = dump_agent_context(history, output_format="markdown")
    assert "valid_tool" in output
    assert '"key": "value"' in output
