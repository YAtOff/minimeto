from unittest.mock import MagicMock, patch

import pytest

from meto.agent.context import Context
from meto.agent.tools.skill_tools import (
    handle_load_agent,
    handle_load_skill,
    load_agent,
    load_skill,
)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=Context)
    ctx.active_skill = None
    return ctx


def test_load_skill_success(mock_context):
    with patch("meto.agent.tools.skill_tools.get_skill_loader") as mock_get_loader:
        mock_loader = mock_get_loader.return_value
        mock_loader.has_skill.return_value = True
        mock_loader.get_skill_content.return_value = "skill content"
        mock_loader.list_skill_agents.return_value = ["agent1"]

        result = load_skill(mock_context, "test_skill")
        assert "skill content" in result
        assert "agent1" in result
        assert mock_context.active_skill == "test_skill"


def test_load_skill_not_found(mock_context):
    with patch("meto.agent.tools.skill_tools.get_skill_loader") as mock_get_loader:
        mock_loader = mock_get_loader.return_value
        mock_loader.has_skill.return_value = False
        mock_loader.list_skills.return_value = ["other_skill"]

        result = load_skill(mock_context, "unknown")
        assert "Error: Skill 'unknown' not found" in result
        assert "other_skill" in result


def test_load_agent_success(mock_context):
    mock_context.active_skill = "test_skill"
    with patch("meto.agent.tools.skill_tools.get_skill_loader") as mock_get_loader:
        mock_loader = mock_get_loader.return_value
        mock_loader.get_skill_agent_config.return_value = {"name": "agent1"}

        result = load_agent(mock_context, "agent1")
        assert '"name": "agent1"' in result


def test_load_agent_no_active_skill(mock_context):
    mock_context.active_skill = None
    result = load_agent(mock_context, "agent1")
    assert "Error: No skill is currently active" in result


def test_handle_load_skill(mock_context):
    with patch("meto.agent.tools.skill_tools.load_skill") as mock_load:
        mock_load.return_value = "skill data"
        params = {"skill_name": "test"}
        result = handle_load_skill(mock_context, params)
        assert result == "skill data"
        mock_load.assert_called_once_with(mock_context, "test")


def test_handle_load_agent(mock_context):
    with patch("meto.agent.tools.skill_tools.load_agent") as mock_load:
        mock_load.return_value = "agent data"
        params = {"agent_name": "bot"}
        result = handle_load_agent(mock_context, params)
        assert result == "agent data"
        mock_load.assert_called_once_with(mock_context, "bot")
