from meto.agent.autopilot.models import AutopilotSession, AutopilotTask, AutopilotTaskStatus


def test_autopilot_session_progress():
    roadmap = [
        AutopilotTask(id="1", description="Task 1", status=AutopilotTaskStatus.COMPLETED),
        AutopilotTask(id="2", description="Task 2", status=AutopilotTaskStatus.PENDING),
    ]
    session = AutopilotSession(goal="Goal", roadmap=roadmap)
    assert session.progress == (1, 2)


def test_get_next_pending_task():
    roadmap = [
        AutopilotTask(id="1", description="Task 1", status=AutopilotTaskStatus.COMPLETED),
        AutopilotTask(id="2", description="Task 2", status=AutopilotTaskStatus.PENDING),
        AutopilotTask(id="3", description="Task 3", status=AutopilotTaskStatus.PENDING),
    ]
    session = AutopilotSession(goal="Goal", roadmap=roadmap)
    next_task = session.get_next_pending_task()
    assert next_task is not None
    assert next_task.id == "2"


def test_get_task():
    roadmap = [
        AutopilotTask(id="1", description="Task 1", status=AutopilotTaskStatus.PENDING),
    ]
    session = AutopilotSession(goal="Goal", roadmap=roadmap)
    task = session.get_task("1")
    assert task is not None
    assert task.description == "Task 1"
    assert session.get_task("99") is None
