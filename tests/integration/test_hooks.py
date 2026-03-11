from unittest.mock import patch

from meto.agent.context import Context
from meto.agent.hooks import (
    InjectedResult,
    PostToolUseHook,
    PreToolUseHook,
    SuccessResult,
    post_tool_use,
    pre_tool_use,
)
from meto.agent.hooks.permissions import ShellPermissionHook
from meto.agent.session import Session
from meto.agent.todo import TodoManager


def test_pre_tool_hook_receives_context():
    """Test that pre-tool hooks receive the context object."""
    session = Session.new()
    context = Context(todos=TodoManager(), history=[], session=session)

    # Define a mock hook class
    class MockHook(PreToolUseHook):
        matched_tools = ["read_file"]

        def run(self):
            return SuccessResult()

    # Patch the registry to only contain our mock hook
    with patch.object(PreToolUseHook, "registry", [MockHook]):
        # We need to mock the MockHook instance creation to verify arguments
        with patch.object(MockHook, "__init__", return_value=None) as mock_init:
            # We also need to mock matches to return True since __init__ is mocked
            with patch.object(MockHook, "matches", return_value=True):
                pre_tool_use("read_file", {"path": "test.py"}, context)

                # Verify hook was initialized with context
                mock_init.assert_called_once()
                call_args = mock_init.call_args
                # __init__(self, tool_name, arguments, context)
                assert call_args[0][0] == "read_file"
                assert call_args[0][1] == {"path": "test.py"}
                assert call_args[0][2] is context


def test_post_tool_hook_receives_context():
    """Test that post-tool hooks receive the context object."""
    session = Session.new()
    context = Context(todos=TodoManager(), history=[], session=session)

    # Define a mock hook class
    class MockPostHook(PostToolUseHook):
        def run(self):
            return SuccessResult()

    # Patch the registry to only contain our mock hook
    with patch.object(PostToolUseHook, "registry", [MockPostHook]):
        # We need to mock the MockPostHook instance creation to verify arguments
        with patch.object(MockPostHook, "__init__", return_value=None) as mock_init:
            # We also need to mock matches to return True since __init__ is mocked
            with patch.object(MockPostHook, "matches", return_value=True):
                post_tool_use("read_file", {"path": "test.py"}, "output", context)

                # Verify hook was initialized with context
                mock_init.assert_called_once()
                call_args = mock_init.call_args
                # __init__(self, tool_name, arguments, output, context)
                assert call_args[0][0] == "read_file"
                assert call_args[0][1] == {"path": "test.py"}
                assert call_args[0][2] == "output"
                assert call_args[0][3] is context


def test_forked_context_has_shared_session_permissions():
    """Test that forked contexts share permission state via the session."""
    session = Session.new()
    parent = Context(todos=TodoManager(), history=[], session=session)
    child = parent.fork()

    # Grant permission in session (shared by both)
    session.permissions["shell:always"] = True

    # Both should have access via shared session
    parent_hook = ShellPermissionHook("shell", {"command": "ls"}, parent)
    child_hook = ShellPermissionHook("shell", {"command": "pwd"}, child)

    assert parent_hook.run().success
    assert child_hook.run().success
    assert child.parent is parent


def test_hook_can_access_parent_context():
    """Test that hooks can access the parent context if it exists."""
    session = Session.new()
    parent = Context(todos=TodoManager(), history=[], session=session)
    child = parent.fork()

    # Define a custom hook that checks for parent context
    class ParentAwareHook(PreToolUseHook):
        matched_tools = ["shell"]

        def run(self):
            if self.context.parent is not None:
                return InjectedResult(injected_content="Has parent")
            return InjectedResult(injected_content="No parent")

    # We manually instantiate and call run(), so no need to patch registry here,
    # but the class definition itself added it to the registry.
    # To be safe, we'll remove it from the registry.
    if ParentAwareHook in PreToolUseHook.registry:
        PreToolUseHook.registry.remove(ParentAwareHook)

    child_hook = ParentAwareHook("shell", {"command": "ls"}, child)
    parent_hook = ParentAwareHook("shell", {"command": "ls"}, parent)

    assert child_hook.run().injected_content == "Has parent"
    assert parent_hook.run().injected_content == "No parent"
