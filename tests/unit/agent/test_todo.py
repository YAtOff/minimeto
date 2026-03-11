import pytest

from meto.agent.todo import TodoManager


def test_todo_manager_init():
    tm = TodoManager()
    assert tm.items == ()
    assert isinstance(tm.items, tuple)


def test_todo_manager_update():
    tm = TodoManager()
    items = [
        {"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing task 2"},
    ]
    tm.update(items)
    assert len(tm.items) == 2
    assert tm.items[0]["content"] == "Task 1"
    assert tm.items[1]["status"] == "in_progress"
    # Verify internal representation uses snake_case but property returns what's stored
    assert tm.items[1]["active_form"] == "Doing task 2"


def test_todo_manager_items_read_only():
    tm = TodoManager()
    with pytest.raises(AttributeError):
        tm.items = []  # type: ignore


def test_todo_manager_items_tuple_is_copy():
    tm = TodoManager()
    items = [{"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"}]
    tm.update(items)

    # Getting items returns a tuple
    current_items = tm.items
    assert isinstance(current_items, tuple)

    # Modifying the list won't affect the tuple if it was a copy,
    # but here we return a new tuple from the list each time.

    # More importantly, you can't mutate the tuple
    with pytest.raises(TypeError):
        tm.items[0] = {}  # type: ignore


def test_todo_manager_validation_max_items():
    tm = TodoManager()
    items = [
        {"content": f"Task {i}", "status": "pending", "activeForm": "Doing"} for i in range(21)
    ]
    with pytest.raises(ValueError, match="Max 20 todos allowed"):
        tm.update(items)


def test_todo_manager_validation_multiple_in_progress():
    tm = TodoManager()
    items = [
        {"content": "Task 1", "status": "in_progress", "activeForm": "Doing 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Doing 2"},
    ]
    with pytest.raises(ValueError, match="Only one todo can be in_progress at a time"):
        tm.update(items)


def test_todo_manager_clear():
    tm = TodoManager()
    tm.update([{"content": "Task 1", "status": "pending", "activeForm": "Doing"}])
    assert len(tm.items) == 1
    tm.clear()
    assert len(tm.items) == 0


def test_todo_manager_render():
    tm = TodoManager()
    tm.update(
        [
            {"content": "Completed", "status": "completed", "activeForm": "Was doing"},
            {"content": "In Progress", "status": "in_progress", "activeForm": "Doing now"},
            {"content": "Pending", "status": "pending", "activeForm": "Will do"},
        ]
    )
    rendered = tm.render()
    assert "[x] Completed" in rendered
    assert "[>] In Progress <- Doing now" in rendered
    assert "[ ] Pending" in rendered
    assert "(1/3 completed)" in rendered
