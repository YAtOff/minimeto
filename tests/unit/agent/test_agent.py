import pytest

from meto.agent.agent import Agent


def test_agent_tools_is_tuple():
    agent = Agent(name="test", prompt="", allowed_tools="*", max_turns=10)
    assert isinstance(agent.tools, tuple)


def test_agent_tools_is_immutable():
    agent = Agent(name="test", prompt="", allowed_tools="*", max_turns=10)
    with pytest.raises(AttributeError):
        # This will fail because it's a tuple, but wait...
        # agent.tools is an attribute, if I try to .append() it will fail with AttributeError
        # because tuple doesn't have append.
        agent.tools.append({"test": "tool"})


def test_agent_tool_names():
    agent = Agent(name="test", prompt="", allowed_tools=[], max_turns=10)
    assert agent.tool_names == []


def test_agent_max_turns_validation():
    with pytest.raises(ValueError, match="max_turns must be at least 1"):
        Agent(name="test", prompt="", allowed_tools="*", max_turns=0)

    with pytest.raises(ValueError, match="max_turns must be at least 1"):
        Agent(name="test", prompt="", allowed_tools="*", max_turns=-1)


def test_agent_unique_tool_names_init():
    # Mock some tool schemas with duplicate names
    agent = Agent(name="test", prompt="", allowed_tools=[], max_turns=10)

    with pytest.raises(ValueError, match="Tool names must be unique"):
        agent.tools = (
            {"function": {"name": "tool1"}},
            {"function": {"name": "tool1"}},
        )


def test_agent_properties_read_only():
    agent = Agent(name="test", prompt="prompt", allowed_tools=[], max_turns=10)

    assert agent.name == "test"
    assert agent.prompt == "prompt"
    assert agent.max_turns == 10

    with pytest.raises(AttributeError):
        agent.name = "new_name"  # type: ignore

    with pytest.raises(AttributeError):
        agent.prompt = "new_prompt"  # type: ignore

    with pytest.raises(AttributeError):
        agent.max_turns = 20  # type: ignore


def test_agent_tools_setter_validation():
    agent = Agent(name="test", prompt="", allowed_tools=[], max_turns=10)

    valid_tools = (
        {"function": {"name": "tool1"}},
        {"function": {"name": "tool2"}},
    )
    agent.tools = valid_tools
    assert agent.tools == valid_tools

    invalid_tools = (
        {"function": {"name": "tool1"}},
        {"function": {"name": "tool1"}},
    )
    with pytest.raises(ValueError, match="Tool names must be unique"):
        agent.tools = invalid_tools


def test_subagent_logging_on_fallback():
    """Test that subagent logs a debug message when falling back to global agents."""
    from unittest.mock import MagicMock, patch

    from meto.agent.exceptions import SkillAgentNotFoundError

    # Mock skill_loader.get_skill_agent_config to raise SkillAgentNotFoundError
    mock_skill_loader = MagicMock()
    mock_skill_loader.get_skill_agent_config.side_effect = SkillAgentNotFoundError(
        "Agent 'nonexistent' not found in skill 'test_skill'"
    )

    # Mock get_skill_loader to return our mock_skill_loader
    # Mock get_agents to return a dict with our agent
    mock_agents = {"nonexistent": {"prompt": "Global prompt", "tools": ["tool1"]}}

    with (
        patch("meto.agent.agent.get_skill_loader", return_value=mock_skill_loader),
        patch("meto.agent.agent.get_agents", return_value=mock_agents),
        patch("meto.agent.agent.logger") as mock_logger,
    ):
        agent = Agent.subagent("nonexistent", skill_name="test_skill")

        # Verify agent was created from global agents
        assert agent.name == "nonexistent"
        assert agent.prompt == "Global prompt"

        # Verify logger.debug was called
        mock_logger.debug.assert_called_once()
        args, _ = mock_logger.debug.call_args
        assert "Skill-local agent 'nonexistent' not found in skill 'test_skill'" in args[0]
        assert "Falling back to global agents" in args[0]
