"""Unit tests for skill expansion."""

from unittest.mock import patch

from meto.agent.loaders.skill_expander import SkillExpander


def test_expand_arguments():
    expander = SkillExpander()
    content = "Args: $ARGUMENTS"
    args = ["one", "two", "three"]

    expanded = expander.expand(content, args)
    assert expanded == "Args: one two three"


def test_expand_indexed_arguments():
    expander = SkillExpander()
    content = "First: $ARGUMENTS[0], Third: $ARGUMENTS[2], Out: $ARGUMENTS[5]"
    args = ["one", "two", "three"]

    expanded = expander.expand(content, args)
    assert expanded == "First: one, Third: three, Out: "


def test_expand_commands():
    expander = SkillExpander()
    content = "Date: $(echo 2026)"

    with patch("meto.agent.loaders.skill_expander.run_shell") as mock_run:
        mock_run.return_value = "2026"
        expanded = expander.expand(content, [])
        assert expanded == "Date: 2026"
        mock_run.assert_called_once_with("echo 2026")


def test_expand_mixed():
    expander = SkillExpander()
    content = "Hello $ARGUMENTS[0], today is $(date +%Y). All: $ARGUMENTS"
    args = ["Alice", "Bob"]

    with patch("meto.agent.loaders.skill_expander.run_shell") as mock_run:
        mock_run.return_value = "2026"
        expanded = expander.expand(content, args)
        assert expanded == "Hello Alice, today is 2026. All: Alice Bob"
