from unittest.mock import MagicMock, patch

import pytest

from meto.agent.context import Context
from meto.agent.exceptions import AgentInterrupted, MaxStepsExceededError
from meto.agent.tools.task_tools import (
    execute_task,
    handle_manage_todos,
    handle_run_task,
    manage_todos,
)


@pytest.fixture
def mock_context():
    ctx = MagicMock(spec=Context)
    ctx.todos = MagicMock()
    ctx.active_skill = "some_skill"
    return ctx


def test_manage_todos_success(mock_context):
    mock_context.todos.update.return_value = "todos updated"
    items = [{"task": "test", "status": "todo"}]

    result = manage_todos(mock_context, items)
    assert result == "todos updated"
    mock_context.todos.update.assert_called_once_with(items)
    mock_context.todos.print_rich.assert_called_once()


def test_execute_task_success(mock_context):
    with patch("meto.agent.agent.Agent.subagent") as mock_subagent:
        with patch("meto.agent.agent_loop.run_agent_loop") as mock_run_loop:
            mock_run_loop.return_value = ["output line 1", "output line 2"]

            result = execute_task(mock_context, "do something", "worker")
            assert "output line 1" in result
            assert "output line 2" in result
            mock_subagent.assert_called_once_with("worker", skill_name="some_skill")


def test_execute_task_interrupted(mock_context):
    with patch("meto.agent.agent.Agent.subagent"):
        with patch("meto.agent.agent_loop.run_agent_loop") as mock_run_loop:
            mock_run_loop.side_effect = AgentInterrupted()

            result = execute_task(mock_context, "do something", "worker")
            assert result == "(subagent cancelled by user)"


def test_execute_task_max_steps(mock_context):
    with patch("meto.agent.agent.Agent.subagent"):
        with patch("meto.agent.agent_loop.run_agent_loop") as mock_run_loop:
            mock_run_loop.side_effect = MaxStepsExceededError("Too many steps")

            result = execute_task(mock_context, "do something", "worker")
            assert "subagent exceeded maximum turns" in result
            assert "Too many steps" in result


def test_execute_task_generic_error(mock_context):
    with patch("meto.agent.agent.Agent.subagent"):
        with patch("meto.agent.agent_loop.run_agent_loop") as mock_run_loop:
            mock_run_loop.side_effect = ValueError("Some error")

            result = execute_task(mock_context, "do something", "worker")
            assert "subagent error: ValueError: Some error" in result


def test_handle_manage_todos(mock_context):
    with patch("meto.agent.tools.task_tools.manage_todos") as mock_manage:
        mock_manage.return_value = "success"
        params = {"items": [{"a": 1}]}
        result = handle_manage_todos(mock_context, params)
        assert result == "success"
        mock_manage.assert_called_once_with(mock_context, [{"a": 1}])


def test_handle_run_task(mock_context):
    with patch("meto.agent.tools.task_tools.execute_task") as mock_exec:
        mock_exec.return_value = "task done"
        params = {"prompt": "go", "agent_name": "bot", "description": "desc"}
        result = handle_run_task(mock_context, params)
        assert result == "task done"
        mock_exec.assert_called_once_with(mock_context, "go", "bot", "desc")
