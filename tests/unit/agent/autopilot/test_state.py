from pathlib import Path

import pytest

from meto.agent.autopilot.models import AutopilotSession, AutopilotTask
from meto.agent.autopilot.state import AutopilotState


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / ".autopilot_state.json"


def test_save_load_delete_state(state_file: Path):
    state = AutopilotState(state_file)
    session = AutopilotSession(
        goal="Test Goal",
        roadmap=[AutopilotTask(id="1", description="Test Task")],
    )

    # Save
    state.save(session)
    assert state_file.exists()

    # Load in new instance
    new_state = AutopilotState(state_file)
    loaded_session = new_state.load()
    assert loaded_session is not None
    assert loaded_session.goal == "Test Goal"
    assert len(loaded_session.roadmap) == 1
    assert loaded_session.roadmap[0].id == "1"

    # Delete
    state.delete()
    assert not state_file.exists()
    assert state.session is None


def test_load_non_existent_state(state_file: Path):
    state = AutopilotState(state_file)
    assert state.load() is None


def test_atomic_save(state_file: Path):
    state = AutopilotState(state_file)
    session = AutopilotSession(goal="Atomic Goal")

    # Save should not leave .tmp file
    state.save(session)
    assert state_file.exists()
    assert not state_file.with_suffix(".tmp").exists()


def test_state_exists(state_file: Path):
    assert not AutopilotState.exists(state_file)
    state = AutopilotState(state_file)
    state.save(AutopilotSession(goal="Exist test"))
    assert AutopilotState.exists(state_file)


def test_load_corrupted_state(state_file: Path):
    state = AutopilotState(state_file)
    with open(state_file, "w") as f:
        f.write("{invalid: json}")

    assert state.load() is None
    backup_path = state_file.with_suffix(".corrupted")
    assert backup_path.exists()
    with open(backup_path) as f:
        assert f.read() == "{invalid: json}"


def test_load_invalid_schema_state(state_file: Path):
    state = AutopilotState(state_file)
    with open(state_file, "w") as f:
        f.write("{}")

    assert state.load() is None
    backup_path = state_file.with_suffix(".corrupted")
    assert backup_path.exists()
    with open(backup_path) as f:
        assert f.read() == "{}"


def test_delete_state_error(state_file: Path):
    from unittest.mock import patch

    state = AutopilotState(state_file)
    state.save(AutopilotSession(goal="Delete error test"))
    assert state_file.exists()

    with patch.object(Path, "unlink") as mock_unlink:
        mock_unlink.side_effect = OSError("Access denied")
        with pytest.raises(RuntimeError, match="Failed to delete state file: Access denied"):
            state.delete()
