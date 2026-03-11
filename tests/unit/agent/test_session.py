import json
import re
from unittest.mock import patch

import pytest

from meto.agent.exceptions import SessionNotFoundError
from meto.agent.session import Session, generate_session_id


def test_generate_session_id_format():
    session_id = generate_session_id()
    # Format: {timestamp}-{random_suffix}
    # Example: 20240310_143052-abc123
    assert re.match(r"^\d{8}_\d{6}-[a-z0-9]{6}$", session_id)
    # Also verify it matches the validation regex mentioned in docstring
    assert re.match(r"^[a-zA-Z0-9_\-]+$", session_id)


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

    # Check that logger.warning was called for the specific line
    warning_calls = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("Skipping malformed line 2 in session test-session" in m for m in warning_calls)

    # Check that logger.error was called for the summary
    error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
    assert any("Session test-session: Failed to parse 1 lines" in m for m in error_calls)
    assert any("lines: [2]" in m for m in error_calls)

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

    # Verify tree structure after loading with rewind
    assert session.history.head.message["content"] == "msg1"
    assert session.history.head.parent is None  # Root node
    assert len(session.history.head.children) == 1  # Has branch to msg2
    assert session.history.head.children[0].message["content"] == "msg2"

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

    # Before second rewind, verify tree branching
    # msg1 should now have two children: msg2 and msg_new
    root_node = session.history.head.parent.parent
    assert root_node.message["content"] == "msg1"
    assert len(root_node.children) == 2
    assert any(c.message["content"] == "msg2" for c in root_node.children)
    assert any(c.message["content"] == "msg_new" for c in root_node.children)

    success = session.history.log_rewind("new_cp")
    assert success is True
    assert len(session.history) == 2
    assert session.history[-1]["content"] == "msg_new"

    # After second rewind, head should be msg_new
    assert session.history.head.message["content"] == "msg_new"
    assert session.history.head.parent.message["content"] == "msg1"
    assert len(session.history.head.children) == 1
    assert session.history.head.children[0].message["content"] == "msg_after_new"


def test_node_tree_construction():
    """Test that nodes form proper parent-child relationships."""
    from meto.agent.session import Node

    root = Node({"role": "user", "content": "root"})
    child1 = Node({"role": "assistant", "content": "child1"}, parent=root)
    child2 = Node({"role": "user", "content": "child2"}, parent=root)

    assert root.children == (child1, child2)
    assert child1.parent is root
    assert child2.parent is root


def test_session_history_tree_structure():
    """Test that SessionHistory maintains tree structure."""
    from meto.agent.session import SessionHistory

    with patch("meto.agent.session.SessionLogger") as mock_logger:
        history = SessionHistory(mock_logger)

        history.append({"role": "user", "content": "msg1"})
        root = history.head
        assert root is not None
        assert root.parent is None

        history.append({"role": "assistant", "content": "msg2"})
        child1 = history.head
        assert child1 is not None
        assert child1.parent is root
        assert root.children == (child1,)

        history.log_checkpoint("cp1")

        history.append({"role": "user", "content": "msg3"})
        child2 = history.head
        assert child2 is not None
        assert child2.parent is child1
        assert child1.children == (child2,)

        # Rewind to cp1 and add a different branch
        history.log_rewind("cp1")
        assert history.head is child1

        history.append({"role": "user", "content": "msg4"})
        child3 = history.head
        assert child3 is not None
        assert child3.parent is child1
        # Now child1 should have TWO children: child2 and child3
        assert child1.children == (child2, child3)

        # Active path should be root -> child1 -> child3
        active_path = history._get_active_path()
        assert active_path == [root, child1, child3]


def test_session_load_reconstructs_tree(tmp_path):
    """Test that Session.load() properly reconstructs the tree from JSONL."""
    session_id = "tree-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "log.jsonl"

    header = {"session_id": session_id, "working_dir": str(tmp_path)}
    # Branch 1: msg1 -> msg2 -> msg3
    # Branch 2: msg1 -> msg2 -> msg4
    msg1 = {"role": "user", "content": "msg1"}
    msg2 = {"role": "assistant", "content": "msg2"}
    cp1 = {"role": "checkpoint", "name": "cp1"}
    msg3 = {"role": "user", "content": "msg3"}
    rewind = {"role": "rewind", "to_checkpoint": "cp1"}
    msg4 = {"role": "user", "content": "msg4"}

    with open(session_file, "w") as f:
        for item in [header, msg1, msg2, cp1, msg3, rewind, msg4]:
            f.write(json.dumps(item) + "\n")

    session = Session.load(session_id, session_dir=tmp_path)

    # Verify history list
    assert len(session.history) == 3
    assert session.history[0]["content"] == "msg1"
    assert session.history[1]["content"] == "msg2"
    assert session.history[2]["content"] == "msg4"

    # Verify tree structure
    head = session.history.head
    assert head is not None
    assert head.message["content"] == "msg4"

    parent = head.parent
    assert parent is not None
    assert parent.message["content"] == "msg2"

    # parent (msg2) should have two children: msg3 and msg4
    assert len(parent.children) == 2
    child_contents = [c.message["content"] for c in parent.children]
    assert "msg3" in child_contents
    assert "msg4" in child_contents

    grandparent = parent.parent
    assert grandparent is not None
    assert grandparent.message["content"] == "msg1"
    assert grandparent.parent is None
    assert grandparent.children == (parent,)


def test_session_new_persists_yolo_flag(tmp_path):
    """Test that Session.new() persists the yolo flag to the header."""
    with patch("meto.conf.settings.SESSION_DIR", tmp_path):
        session = Session.new(yolo=True)
        assert session.yolo is True

        # Verify header on disk
        log_dir = tmp_path / session.session_id
        session_file = log_dir / "log.jsonl"
        with open(session_file) as f:
            header = json.loads(f.readline())
            assert header["yolo"] is True


def test_session_load_persists_yolo_flag(tmp_path):
    """Test that yolo flag is persisted and restored."""
    session_id = "yolo-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "log.jsonl"

    header = {"session_id": session_id, "working_dir": str(tmp_path), "yolo": True}
    with open(session_file, "w") as f:
        f.write(json.dumps(header) + "\n")

    session = Session.load(session_id, session_dir=tmp_path)
    assert session.yolo is True


def test_session_load_yolo_override(tmp_path):
    """Test that yolo parameter overrides saved value."""
    session_id = "override-session"
    session_dir = tmp_path / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "log.jsonl"

    # Case 1: Saved False, Load True -> Should be True
    header = {"session_id": session_id, "working_dir": str(tmp_path), "yolo": False}
    with open(session_file, "w") as f:
        f.write(json.dumps(header) + "\n")

    session = Session.load(session_id, session_dir=tmp_path, yolo=True)
    assert session.yolo is True

    # Case 2: Saved True, Load False -> Should be True (respects saved value)
    # The current implementation uses: final_yolo = yolo or info.get("yolo", False)
    header = {"session_id": session_id, "working_dir": str(tmp_path), "yolo": True}
    with open(session_file, "w") as f:
        f.write(json.dumps(header) + "\n")

    session = Session.load(session_id, session_dir=tmp_path, yolo=False)
    assert session.yolo is True

    # Case 3: Saved False, Load False -> Should be False
    header = {"session_id": session_id, "working_dir": str(tmp_path), "yolo": False}
    with open(session_file, "w") as f:
        f.write(json.dumps(header) + "\n")

    session = Session.load(session_id, session_dir=tmp_path, yolo=False)
    assert session.yolo is False
