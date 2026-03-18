from meto.agent.autopilot.pruning import summarize_tool_output


def test_summarize_tool_output_skips_images():
    # Arrange
    tool_name = "test_tool"
    image_data = "a" * 3000
    image_output = f"__METO_IMAGE__:{image_data}"
    max_chars = 2000

    # Act
    result = summarize_tool_output(tool_name, image_output, max_chars=max_chars)

    # Assert
    assert result == image_output
    assert len(result) > max_chars
