"""Unit tests for the /use slash command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from meto.agent.command import chat_commands
from meto.agent.session import Session


@pytest.fixture
def session():
    return Session.new()


@pytest.fixture
def runner():
    return CliRunner()


@patch("meto.agent.command.get_skill_loader")
@patch("meto.agent.command.run_agent_loop")
def test_use_command_basic(mock_run_loop, mock_get_loader, runner, session):
    # Mock skill config
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader
    mock_loader.has_skill.return_value = True
    mock_loader.get_skill_config.return_value = {
        "name": "test-skill",
        "content": "Hello $ARGUMENTS[0]",
        "allowed_tools": "*",
    }

    mock_run_loop.return_value = iter(["Agent response"])

    result = runner.invoke(chat_commands, ["use", "test-skill", "Alice"], obj={"session": session})

    assert result.exit_code == 0
    assert "Agent response" in result.output

    # Verify run_agent_loop was called with expanded body
    mock_run_loop.assert_called_once()
    args, _ = mock_run_loop.call_args
    # args[1] is the prompt (expanded body)
    assert args[1] == "Hello Alice"


@patch("meto.agent.command.get_skill_loader")
@patch("meto.agent.command.run_agent_loop")
def test_use_command_fork(mock_run_loop, mock_get_loader, runner, session):
    # Mock skill config with context: fork
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader
    mock_loader.has_skill.return_value = True
    mock_loader.get_skill_config.return_value = {
        "name": "fork-skill",
        "content": "Task for fork",
        "context": "fork",
        "allowed_tools": ["read_file"],
    }

    mock_run_loop.return_value = iter(["Fork response"])

    result = runner.invoke(chat_commands, ["use", "fork-skill"], obj={"session": session})

    assert result.exit_code == 0
    assert "[Forked context:" in result.output
    assert "Fork response" in result.output

    # Verify run_agent_loop was called with restricted tools
    mock_run_loop.assert_called_once()
    agent_arg = mock_run_loop.call_args[0][0]
    assert agent_arg.tool_names == ["read_file"]
    assert agent_arg.name == "fork"


@patch("meto.agent.command.get_skill_loader")
@patch("meto.agent.command.run_agent_loop")
def test_use_command_implicit_fork(mock_run_loop, mock_get_loader, runner, session):
    # Mock skill config with agent
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader
    mock_loader.has_skill.return_value = True
    mock_loader.get_skill_config.return_value = {
        "name": "subagent-skill",
        "content": "Task for subagent",
        "agent": "explore",
        "allowed_tools": ["read_file"],
    }

    # We need to patch Agent.subagent since we rely on it
    with patch("meto.agent.command.Agent.subagent") as mock_subagent:
        mock_agent_instance = MagicMock()
        mock_agent_instance.tool_names = ["read_file", "grep_search", "shell"]
        mock_agent_instance.name = "explore"
        mock_subagent.return_value = mock_agent_instance

        mock_run_loop.return_value = iter(["Subagent response"])

        result = runner.invoke(chat_commands, ["use", "subagent-skill"], obj={"session": session})

        assert result.exit_code == 0
        assert "[Forked context:" in result.output
        assert "Subagent response" in result.output

        # Verify run_agent_loop was called
        mock_run_loop.assert_called_once()
        mock_subagent.assert_called_once_with("explore", skill_name="subagent-skill")


@patch("meto.agent.command.get_skill_loader")
def test_use_command_not_found(mock_get_loader, runner, session):
    mock_loader = MagicMock()
    mock_get_loader.return_value = mock_loader
    mock_loader.has_skill.return_value = False
    mock_loader.list_skills.return_value = ["skill1", "skill2"]

    result = runner.invoke(chat_commands, ["use", "ghost-skill"], obj={"session": session})

    assert result.exit_code == 0
    assert "Error: Skill 'ghost-skill' not found" in result.output
