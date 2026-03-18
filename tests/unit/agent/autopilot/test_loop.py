from unittest.mock import patch

import pytest

from meto.agent.autopilot.loop import run_autopilot_loop
from meto.agent.autopilot.models import AutopilotSession, AutopilotTask, AutopilotTaskStatus
from meto.agent.context import Context
from meto.agent.exceptions import AgentInterrupted
from meto.agent.todo import TodoManager


@pytest.fixture
def mock_session():
    task = AutopilotTask(id="1.1", description="Test task")
    return AutopilotSession(goal="Test goal", roadmap=[task])


@pytest.fixture
def mock_context():
    return Context(todos=TodoManager(), history=[])


def test_run_autopilot_loop_interrupted(mock_session, mock_context):
    with (
        patch("meto.agent.autopilot.loop.AutopilotState") as mock_state_cls,
        patch("meto.agent.autopilot.loop.Agent"),
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
        patch("meto.agent.autopilot.loop.assemble_context_capsule", return_value="Sub prompt"),
        patch("meto.agent.autopilot.loop.Console"),
        patch("meto.agent.autopilot.loop.autopilot_commit", return_value=True),
    ):
        mock_state = mock_state_cls.return_value
        mock_state.load.return_value = mock_session

        # Simulate AgentInterrupted during run_agent_loop
        mock_run_agent_loop.side_effect = AgentInterrupted("User interrupted")

        # We expect AgentInterrupted to be re-raised
        with pytest.raises(AgentInterrupted):
            list(run_autopilot_loop("Test goal", mock_context))

        # Verify task status was updated to FAILED
        task = mock_session.get_task("1.1")
        assert task.status == AutopilotTaskStatus.FAILED
        assert task.error == "Interrupted by user"

        # Verify it didn't retry (only one attempt)
        assert task.attempts == 1


def test_run_autopilot_loop_exception_retries(mock_session, mock_context):
    with (
        patch("meto.agent.autopilot.loop.AutopilotState") as mock_state_cls,
        patch("meto.agent.autopilot.loop.Agent"),
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
        patch("meto.agent.autopilot.loop.assemble_context_capsule", return_value="Sub prompt"),
        patch("meto.agent.autopilot.loop.Console"),
        patch("meto.agent.autopilot.loop.autopilot_commit", return_value=True),
    ):
        mock_state = mock_state_cls.return_value
        mock_state.load.return_value = mock_session

        # Simulate Exception during run_agent_loop
        mock_run_agent_loop.side_effect = Exception("General error")

        # It should retry 3 times and then break the loop (not raise)
        list(run_autopilot_loop("Test goal", mock_context))

        # Verify task status was updated to FAILED after retries
        task = mock_session.get_task("1.1")
        assert task.status == AutopilotTaskStatus.FAILED
        assert "General error" in task.error

        # Verify it retried 3 times
        assert task.attempts == 3


def test_generate_roadmap_success(mock_context):
    from meto.agent.autopilot.loop import _generate_roadmap

    session = AutopilotSession(goal="Test goal", roadmap=[])

    planner_output = (
        "Here is the plan:\n"
        "### 🚀 AUTOPILOT_ROADMAP\n"
        "### 🎯 Task: 1.1 | Implement feature A\n"
        "### 🎯 Task: 1.2 | Test feature A\n"
    )

    with (
        patch("meto.agent.autopilot.loop.Agent") as mock_agent_cls,
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
    ):
        mock_run_agent_loop.return_value = iter([planner_output])

        # Consume the generator
        list(_generate_roadmap(session, mock_context))

        mock_agent_cls.subagent.assert_called_once_with("plan")
        assert len(session.roadmap) == 2
        assert session.roadmap[0].id == "1.1"
        assert session.roadmap[0].description == "Implement feature A"
        assert session.roadmap[1].id == "1.2"
        assert session.roadmap[1].description == "Test feature A"


def test_run_autopilot_loop_roadmap_failure(mock_context):
    with (
        patch("meto.agent.autopilot.loop.AutopilotState") as mock_state_cls,
        patch("meto.agent.autopilot.loop.Agent"),
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
        patch("meto.agent.autopilot.loop.Console"),
    ):
        mock_state = mock_state_cls.return_value
        # No roadmap in session
        mock_session = AutopilotSession(goal="Test goal", roadmap=[])
        mock_state.load.return_value = mock_session

        # Planner output with no roadmap
        mock_run_agent_loop.return_value = iter(["Plan without structured roadmap"])

        gen = run_autopilot_loop("Test goal", mock_context)
        outputs = []
        with pytest.raises(RuntimeError, match="Failed to parse roadmap from planner output"):
            for chunk in gen:
                outputs.append(chunk)

        assert any("❌ Autopilot Error:" in out for out in outputs)
        assert any("No structured roadmap found in planner output" in out for out in outputs)


def test_task_execution_success(mock_session, mock_context):
    with (
        patch("meto.agent.autopilot.loop.AutopilotState") as mock_state_cls,
        patch("meto.agent.autopilot.loop.Agent"),
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
        patch("meto.agent.autopilot.loop.assemble_context_capsule", return_value="Sub prompt"),
        patch("meto.agent.autopilot.loop.Console"),
        patch("meto.agent.autopilot.loop.autopilot_commit", return_value=True) as mock_commit,
    ):
        mock_state = mock_state_cls.return_value
        mock_state.load.return_value = mock_session

        # Mock run_agent_loop to return success message
        mock_run_agent_loop.return_value = iter(["Task completed successfully"])

        # Run the loop
        list(run_autopilot_loop("Test goal", mock_context))

        # Verify task status was updated to COMPLETED
        task = mock_session.get_task("1.1")
        assert task.status == AutopilotTaskStatus.COMPLETED

        # Verify commit was called
        mock_commit.assert_called_once_with(task)


def test_run_autopilot_loop_git_failure_retries(mock_session, mock_context):
    with (
        patch("meto.agent.autopilot.loop.AutopilotState") as mock_state_cls,
        patch("meto.agent.autopilot.loop.Agent"),
        patch("meto.agent.autopilot.loop.run_agent_loop") as mock_run_agent_loop,
        patch("meto.agent.autopilot.loop.assemble_context_capsule", return_value="Sub prompt"),
        patch("meto.agent.autopilot.loop.Console"),
        patch("meto.agent.autopilot.loop.autopilot_commit") as mock_commit,
    ):
        mock_state = mock_state_cls.return_value
        mock_state.load.return_value = mock_session

        # Mock run_agent_loop to return success message
        mock_run_agent_loop.return_value = iter(["Task completed successfully"])

        # Simulate RuntimeError during autopilot_commit
        mock_commit.side_effect = RuntimeError("Git commit failed: details")

        # It should retry 3 times and then break the loop (not raise)
        list(run_autopilot_loop("Test goal", mock_context))

        # Verify task status was updated to FAILED after retries
        task = mock_session.get_task("1.1")
        assert task.status == AutopilotTaskStatus.FAILED
        assert "Git commit failed: details" in task.error

        # Verify it retried 3 times
        assert task.attempts == 3


def test_get_next_pending_task_skips_completed():
    tasks = [
        AutopilotTask(id="1.1", description="Task 1", status=AutopilotTaskStatus.COMPLETED),
        AutopilotTask(id="1.2", description="Task 2", status=AutopilotTaskStatus.PENDING),
        AutopilotTask(id="1.3", description="Task 3", status=AutopilotTaskStatus.PENDING),
    ]
    session = AutopilotSession(goal="Test goal", roadmap=tasks)

    next_task = session.get_next_pending_task()
    assert next_task.id == "1.2"

    tasks[1].status = AutopilotTaskStatus.COMPLETED
    next_task = session.get_next_pending_task()
    assert next_task.id == "1.3"
