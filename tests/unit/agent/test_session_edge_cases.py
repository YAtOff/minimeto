from unittest.mock import MagicMock

from meto.agent.session import SessionHistory


def test_rewind_to_earlier_checkpoint_with_later_branches():
    """Test rewinding past intermediate branches.

    Structure:
    msg1 -> cp1 -> msg2 -> msg3 -> cp2 -> msg4
    """
    mock_logger = MagicMock()
    history = SessionHistory(mock_logger)

    # msg1
    history.append({"role": "user", "content": "msg1"})
    msg1_node = history.head

    # cp1
    history.log_checkpoint("cp1")
    cp1_node = history.head
    assert cp1_node == msg1_node

    # msg2
    history.append({"role": "assistant", "content": "msg2"})
    msg2_node = history.head

    # msg3
    history.append({"role": "user", "content": "msg3"})
    msg3_node = history.head

    # cp2
    history.log_checkpoint("cp2")
    cp2_node = history.head
    assert cp2_node == msg3_node

    # msg4
    history.append({"role": "assistant", "content": "msg4"})

    assert len(history) == 4
    assert [m["content"] for m in history] == ["msg1", "msg2", "msg3", "msg4"]

    # Rewind to cp1
    success = history.log_rewind("cp1")
    assert success is True
    assert history.head == cp1_node
    assert len(history) == 1
    assert history[0]["content"] == "msg1"

    # Add msg5
    history.append({"role": "user", "content": "msg5"})
    msg5_node = history.head

    # Verify tree structure has two branches from cp1
    # cp1_node is msg1_node. It should now have two children: msg2_node and msg5_node
    assert len(cp1_node.children) == 2
    assert msg2_node in cp1_node.children
    assert msg5_node in cp1_node.children

    # Active path should be msg1 -> msg5
    assert len(history) == 2
    assert [m["content"] for m in history] == ["msg1", "msg5"]


def test_checkpoint_with_no_head():
    """Test creating checkpoint when head is None."""
    mock_logger = MagicMock()
    history = SessionHistory(mock_logger)
    assert history.head is None

    # Should handle gracefully without crashing and NOT create a checkpoint
    history.log_checkpoint("empty_cp")
    assert "empty_cp" not in history.checkpoints
    mock_logger.log_checkpoint.assert_not_called()


def test_rewind_to_non_existent_checkpoint():
    """Test rewinding to a checkpoint that doesn't exist."""
    mock_logger = MagicMock()
    history = SessionHistory(mock_logger)

    history.append({"role": "user", "content": "msg1"})

    success = history.log_rewind("non_existent")
    assert success is False
    assert len(history) == 1
    assert history[0]["content"] == "msg1"


def test_multiple_checkpoints_at_same_node():
    """Test multiple checkpoints pointing to the same node."""
    mock_logger = MagicMock()
    history = SessionHistory(mock_logger)

    history.append({"role": "user", "content": "msg1"})
    node1 = history.head

    history.log_checkpoint("cp1")
    history.log_checkpoint("cp2")

    assert history.checkpoints["cp1"] == node1
    assert history.checkpoints["cp2"] == node1

    history.append({"role": "assistant", "content": "msg2"})
    assert len(history) == 2

    history.log_rewind("cp1")
    assert len(history) == 1
    assert history.head == node1

    history.append({"role": "assistant", "content": "msg3"})
    history.log_rewind("cp2")
    assert len(history) == 1
    assert history.head == node1


def test_rewind_to_root():
    """Test rewinding to a checkpoint at the very first message."""
    mock_logger = MagicMock()
    history = SessionHistory(mock_logger)

    history.append({"role": "user", "content": "msg1"})
    history.log_checkpoint("root_cp")

    history.append({"role": "assistant", "content": "msg2"})
    history.append({"role": "user", "content": "msg3"})

    assert len(history) == 3

    history.log_rewind("root_cp")
    assert len(history) == 1
    assert history[0]["content"] == "msg1"
    assert history.head.parent is None
