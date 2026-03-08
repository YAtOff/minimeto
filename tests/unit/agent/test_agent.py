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
