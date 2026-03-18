from meto.agent.tool_schema import TOOLS_BY_NAME

def test_read_file_schema_mentions_images():
    """Test that the read_file tool schema description mentions image support."""
    read_file_tool = TOOLS_BY_NAME.get("read_file")
    assert read_file_tool is not None
    description = read_file_tool["function"]["description"]
    assert "image" in description.lower()
