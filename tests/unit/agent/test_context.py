from __future__ import annotations

from pathlib import Path

import pytest

from meto.agent.context import Context, PendingTool
from meto.agent.exceptions import ContextForkError
from meto.agent.session import Session, SessionHistory, SessionLogger
from meto.agent.todo import TodoManager


def test_context_fork_creates_child_context():
    """Test that fork creates a properly configured child context."""
    todos = TodoManager()
    parent = Context(
        todos=todos, history=[{"role": "user", "content": "hi"}], context_id="parent-id"
    )
    child = parent.fork()

    assert child.parent is parent
    assert child.todos is parent.todos  # Same object
    assert child.context_id != parent.context_id
    assert len(child.history) == 0  # Fresh history
    assert child.session is None


def test_context_fork_with_session_history(tmp_path: Path):
    """Test that fork creates nested child logger."""
    # Setup a session
    session_id = "test-session"
    log_dir = tmp_path / session_id
    session_logger = SessionLogger(session_id, log_dir=log_dir)
    history = SessionHistory(session_logger)
    session = Session(session_id=session_id, working_dir=tmp_path, history=history)

    todos = TodoManager()
    context = Context(todos=todos, history=history, session=session, context_id=session_id)

    child = context.fork()

    assert child.todos is todos
    assert len(child.history) == 0
    assert child.parent is context
    assert child.session is session
    assert isinstance(child._history, SessionHistory)

    # Verify child logger is in children/ subdirectory
    assert child.context_id is not None
    expected_log_dir = log_dir / "children" / child.context_id
    assert child._history.session_logger.log_dir == expected_log_dir
    assert expected_log_dir.exists()
    assert (expected_log_dir / "log.jsonl").exists()


def test_context_fork_preserves_active_skill():
    """Test that active_skill is preserved in forked contexts."""
    todos = TodoManager()
    parent = Context(todos=todos, history=[], active_skill="test_skill")
    child = parent.fork()
    assert child.active_skill == "test_skill"


def test_context_fork_unique_ids():
    """Test that multiple forks have unique IDs."""
    todos = TodoManager()
    parent = Context(todos=todos, history=[])
    child1 = parent.fork()
    child2 = parent.fork()

    assert child1.context_id != child2.context_id
    assert child1.context_id != parent.context_id


def test_context_validation():
    """Test that Context validates its inputs."""
    todos = TodoManager()

    # Valid
    Context(todos=todos)

    # Invalid todos
    with pytest.raises(TypeError, match="todos must be a TodoManager"):
        Context(todos="not-a-todo-manager")  # type: ignore

    # Invalid pending_tools
    with pytest.raises(TypeError, match="pending_tools must contain PendingTool instances"):
        Context(todos=todos, pending_tools=[{"name": "test"}])  # type: ignore


def test_add_pending_tool():
    """Test adding pending tools via add_pending_tool."""
    todos = TodoManager()
    context = Context(todos=todos)

    tool = PendingTool(schema={"function": {"name": "test"}}, handler=lambda x, y: "ok")
    context.add_pending_tool(tool)

    assert len(context.pending_tools) == 1
    assert context.pending_tools[0] == tool

    with pytest.raises(TypeError, match="tool must be a PendingTool"):
        context.add_pending_tool({"not": "a-tool"})  # type: ignore


def test_pending_tool_validation():
    """Test PendingTool schema validation and name matching."""

    # Valid
    def my_handler(ctx, params):
        return "ok"

    PendingTool(schema={"function": {"name": "my_handler"}}, handler=my_handler)

    # Valid with handle_ prefix
    def handle_test(ctx, params):
        return "ok"

    PendingTool(schema={"function": {"name": "test"}}, handler=handle_test)

    # Missing function key
    with pytest.raises(ValueError, match="PendingTool schema must contain 'function' key"):
        PendingTool(schema={}, handler=my_handler)

    # Missing name key
    with pytest.raises(ValueError, match="PendingTool schema must contain 'function.name'"):
        PendingTool(schema={"function": {}}, handler=my_handler)

    # Non-callable handler
    with pytest.raises(ValueError, match="PendingTool handler must be callable"):
        PendingTool(schema={"function": {"name": "test"}}, handler="not-callable")  # type: ignore


def test_pending_tool_immutability():
    """Test that PendingTool is frozen."""

    def my_handler(ctx, params):
        return "ok"

    tool = PendingTool(schema={"function": {"name": "test"}}, handler=my_handler)

    with pytest.raises(AttributeError):
        tool.handler = lambda x, y: "new"  # type: ignore


def test_context_fork_isolates_pending_tools():
    """Test that pending_tools are not inherited by forked contexts."""
    todos = TodoManager()
    tool = PendingTool(schema={"function": {"name": "test"}}, handler=lambda x, y: "ok")
    parent = Context(
        todos=todos,
        history=[],
        pending_tools=[tool],
    )
    child = parent.fork()
    assert len(child.pending_tools) == 0
    assert parent.pending_tools != child.pending_tools


def test_context_fork_history_isolation():
    """Test that adding messages to child history does not affect parent."""
    todos = TodoManager()
    parent = Context(todos=todos, history=[{"role": "user", "content": "parent msg"}])
    child = parent.fork()

    child.add_message({"role": "user", "content": "child msg"})

    assert len(parent.history) == 1
    assert parent.history[0]["content"] == "parent msg"
    assert len(child.history) == 1
    assert child.history[0]["content"] == "child msg"


def test_context_fork_logging_failure_raises_context_fork_error(tmp_path: Path):
    """Test that context fork raises ContextForkError when logging setup fails."""
    # Setup parent session
    session_id = "parent-session"
    log_dir = tmp_path / session_id
    session_logger = SessionLogger(session_id, log_dir=log_dir)
    history = SessionHistory(session_logger)
    session = Session(session_id=session_id, working_dir=tmp_path, history=history)

    todos = TodoManager()
    context = Context(todos=todos, history=history, session=session, context_id=session_id)

    # Create a 'children' directory and make it read-only
    children_dir = log_dir / "children"
    children_dir.mkdir(parents=True)
    children_dir.chmod(0o555)  # Read & execute only (no write)

    try:
        with pytest.raises(ContextForkError) as excinfo:
            context.fork()

        assert "Failed to create forked logging context" in str(excinfo.value)
    finally:
        # Restore permissions for cleanup
        children_dir.chmod(0o755)
