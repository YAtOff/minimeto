from meto.agent.autopilot.context_capsule import assemble_context_capsule
from meto.agent.autopilot.models import AutopilotSession, AutopilotTask


def test_assemble_context_capsule_first_task():
    roadmap = [
        AutopilotTask(id="1.1", description="Task 1"),
        AutopilotTask(id="1.2", description="Task 2"),
    ]
    session = AutopilotSession(goal="Main Goal", roadmap=roadmap)

    capsule = assemble_context_capsule(session, roadmap[0])
    assert "### 🎯 Global Goal\nMain Goal" in capsule
    assert "### 🛠️ Current Task\nTask 1" in capsule
    assert "Previous Task Handover" not in capsule


def test_assemble_context_capsule_second_task_with_handover():
    roadmap = [
        AutopilotTask(id="1.1", description="Task 1", handover="Handover content 1"),
        AutopilotTask(id="1.2", description="Task 2"),
    ]
    session = AutopilotSession(goal="Main Goal", roadmap=roadmap)

    capsule = assemble_context_capsule(session, roadmap[1])
    assert "### 🎯 Global Goal\nMain Goal" in capsule
    assert "### 🛠️ Current Task\nTask 2" in capsule
    assert "### ⬅️ Previous Task Handover (1.1)" in capsule
    assert "Handover content 1" in capsule


def test_assemble_context_capsule_empty_roadmap(caplog):
    session = AutopilotSession(goal="Main Goal", roadmap=[])
    current_task = AutopilotTask(id="1.1", description="Task 1")

    capsule = assemble_context_capsule(session, current_task)
    assert "### 🎯 Global Goal\nMain Goal" in capsule
    assert "### 🛠️ Current Task\nTask 1" in capsule
    assert "Previous Task Handover" not in capsule
    assert "Assembling context capsule with empty roadmap" in caplog.text


def test_assemble_context_capsule_task_not_in_roadmap(caplog):
    roadmap = [
        AutopilotTask(id="1.1", description="Task 1"),
    ]
    session = AutopilotSession(goal="Main Goal", roadmap=roadmap)
    current_task = AutopilotTask(id="1.2", description="Task 2")

    capsule = assemble_context_capsule(session, current_task)
    assert "### 🎯 Global Goal\nMain Goal" in capsule
    assert "### 🛠️ Current Task\nTask 2" in capsule
    assert "Previous Task Handover" not in capsule
    assert "Current task 1.2 not found in roadmap" in caplog.text
