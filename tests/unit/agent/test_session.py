import json

import pytest

from meto.agent.exceptions import SessionNotFoundError
from meto.agent.session import Session


def test_session_load_non_existent_raises(tmp_path):
    session_id = "non-existent"
    session_dir = tmp_path

    with pytest.raises(SessionNotFoundError) as excinfo:
        Session.load(session_id, session_dir=session_dir)

    assert f"Session '{session_id}' not found" in str(excinfo.value)


def test_session_new_creates_unique_ids():
    s1 = Session.new()
    s2 = Session.new()
    assert s1.session_id != s2.session_id


def test_session_id_format_validation():
    with pytest.raises(ValueError, match="Invalid session ID format"):
        Session.load("../traversal")

    with pytest.raises(ValueError, match="Invalid session ID format"):
        Session.load("spaces are not allowed")

    with pytest.raises(ValueError, match="Invalid session ID format"):
        Session.load("special!@#")


from unittest.mock import patch


def test_session_load_malformed_json_logs_warning(tmp_path):
    session_id = "test-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "log.jsonl"

    header = {"session_id": session_id, "working_dir": str(tmp_path)}
    user_msg = {
        "role": "user",
        "content": "hello",
        "timestamp": "2024-03-08T12:00:00Z",
        "session_id": session_id,
    }
    malformed_line = "{malformed json"
    assistant_msg = {
        "role": "assistant",
        "content": "hi",
        "timestamp": "2024-03-08T12:00:01Z",
        "session_id": session_id,
    }

    with open(session_file, "w") as f:
        f.write(json.dumps(header) + "\n")
        f.write(json.dumps(user_msg) + "\n")
        f.write(malformed_line + "\n")
        f.write(json.dumps(assistant_msg) + "\n")

    with patch("meto.agent.session.logger") as mock_logger:
        session = Session.load(session_id, session_dir=tmp_path)

    # Check that logger.warning was called with expected messages
    warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("Skipping malformed line 2 in session test-session" in m for m in warning_calls)
    assert any("skipped 1 malformed lines. History may be incomplete." in m for m in warning_calls)

    assert len(session.history) == 2
    assert session.history[0]["content"] == "hello"
    assert session.history[1]["content"] == "hi"


def test_session_checkpoints_and_rewind(tmp_path):
    session_id = "checkpoint-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "log.jsonl"

    header = {"session_id": session_id, "working_dir": str(tmp_path)}
    msg1 = {"role": "user", "content": "msg1"}
    cp1 = {"role": "checkpoint", "name": "cp1"}
    msg2 = {"role": "user", "content": "msg2"}
    msg3 = {"role": "user", "content": "msg3"}
    cp2 = {"role": "checkpoint", "name": "cp2"}
    msg4 = {"role": "user", "content": "msg4"}
    rewind = {"role": "rewind", "to_checkpoint": "cp1"}

    with open(session_file, "w") as f:
        for item in [header, msg1, cp1, msg2, msg3, cp2, msg4, rewind]:
            f.write(json.dumps(item) + "\n")

    session = Session.load(session_id, session_dir=tmp_path)

    # After loading, the history should be truncated to 'cp1'
    # meaning it should only have msg1. msg2, msg3, msg4 should be discarded.
    assert len(session.history) == 1
    assert session.history[0]["content"] == "msg1"

    # The remaining checkpoints should only be those before or at the rewound state.
    # In this case, 'cp1' should exist, 'cp2' should also technically exist in the checkpoints dict
    # but that's an implementation detail. Wait, actually, cp2's index would be out of bounds,
    # but the test focuses on the content.
    assert "cp1" in session.history.checkpoints

    # Let's test the memory rewind functionality now
    session.history.append({"role": "user", "content": "msg_new"})
    session.history.log_checkpoint("new_cp")
    session.history.append({"role": "user", "content": "msg_after_new"})

    assert len(session.history) == 3
    assert session.history[-1]["content"] == "msg_after_new"

    success = session.history.log_rewind("new_cp")
    assert success is True
    assert len(session.history) == 2
    assert session.history[-1]["content"] == "msg_new"
