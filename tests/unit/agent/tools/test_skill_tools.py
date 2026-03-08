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


def test_load_skill_unexpected_error(mock_context):
    """Test load_skill handles unexpected exceptions with an error ID."""
    with patch("meto.agent.tools.skill_tools.get_skill_loader") as mock_get_loader:
        # Simulate an unexpected error
        mock_get_loader.side_effect = RuntimeError("Something went wrong")

        with patch("meto.agent.tools.skill_tools.logger") as mock_logger:
            result = load_skill(mock_context, "any-skill")

            assert (
                "Error: Failed to load skill 'any-skill' due to an unexpected internal error"
                in result
            )
            assert "Error ID:" in result

            # Verify logging happened
            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args[0][0]
            assert "Unexpected error loading skill" in call_args


def test_load_agent_unexpected_error(mock_context):
    """Test load_agent handles unexpected exceptions with an error ID."""
    mock_context.active_skill = "some-skill"

    with patch("meto.agent.tools.skill_tools.get_skill_loader") as mock_get_loader:
        # Simulate an unexpected error
        mock_get_loader.side_effect = RuntimeError("Something went wrong")

        with patch("meto.agent.tools.skill_tools.logger") as mock_logger:
            result = load_agent(mock_context, "any-agent")

            assert (
                "Error: Failed to load agent 'any-agent' from skill 'some-skill' due to an unexpected internal error"
                in result
            )
            assert "Error ID:" in result

            # Verify logging happened
            mock_logger.exception.assert_called_once()
            call_args = mock_logger.exception.call_args[0][0]
            assert "Unexpected error loading agent" in call_args


def test_error_id_uniqueness():
    """Test that generated error IDs are likely unique."""
    from meto.agent.tools.skill_tools import generate_error_id

    ids = {generate_error_id() for _ in range(100)}
    assert len(ids) == 100
    for eid in ids:
        assert len(eid) == 8
        assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789" for c in eid)
