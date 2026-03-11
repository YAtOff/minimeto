import os
from unittest.mock import patch

from meto.agent.context import Context
from meto.agent.hooks.permissions import (
    FetchPermissionHook,
    FilePermissionHook,
    ShellPermissionHook,
)
from meto.agent.session import Session
from meto.agent.todo import TodoManager
from meto.conf import settings


def test_file_permission_hook_checks_session_permissions(tmp_path):
    """Test that FilePermissionHook uses session permissions."""
    session = Session.new()
    context = Context(todos=TodoManager(), history=[], session=session)

    # Use a path that is definitely outside the current working directory
    # We'll create a temp dir and use it as CWD, then try to access a path outside it
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    outside_path = tmp_path / "outside.txt"
    outside_path.write_text("outside")

    old_cwd = os.getcwd()
    os.chdir(cwd)
    try:
        hook = FilePermissionHook(
            tool_name="write_file", arguments={"path": str(outside_path)}, context=context
        )

        # Ensure permissions are enabled for the test
        with (
            patch.object(settings, "PERMISSIONS_ENABLED", True),
            patch("meto.agent.permissions.PromptSession") as mock_prompt,
        ):
            mock_prompt.return_value.prompt.return_value = "no"
            result = hook.run()
            assert not result.success
            assert "Permission denied" in result.error
    finally:
        os.chdir(old_cwd)


def test_file_permission_hook_inside_cwd(tmp_path):
    """Test that FilePermissionHook allows access inside CWD without check."""
    session = Session.new()
    context = Context(todos=TodoManager(), history=[], session=session)

    cwd = tmp_path / "cwd"
    cwd.mkdir()
    inside_path = cwd / "test.txt"

    old_cwd = os.getcwd()
    os.chdir(cwd)
    try:
        hook = FilePermissionHook(
            tool_name="write_file", arguments={"path": str(inside_path)}, context=context
        )

        # Should succeed without even prompting
        with (
            patch.object(settings, "PERMISSIONS_ENABLED", True),
            patch("meto.agent.permissions.PromptSession") as mock_prompt,
        ):
            result = hook.run()
            assert result.success
            mock_prompt.return_value.prompt.assert_not_called()
    finally:
        os.chdir(old_cwd)


def test_permission_hook_yolo_bypass():
    """Test that yolo mode bypasses all permission checks."""
    session = Session.new(yolo=True)
    context = Context(todos=TodoManager(), history=[], session=session)

    hook = ShellPermissionHook(
        tool_name="shell", arguments={"command": "rm -rf /"}, context=context
    )

    with patch.object(settings, "PERMISSIONS_ENABLED", True):
        # Should allow even without explicit permission
        result = hook.run()
        assert result.success


def test_permissions_isolated_between_sessions():
    """Test that permissions in one session don't affect another."""
    session1 = Session.new()
    session2 = Session.new()

    # Grant permission in session1
    session1.permissions["shell:always"] = True

    # Should not affect session2
    context2 = Context(todos=TodoManager(), history=[], session=session2)
    hook = ShellPermissionHook(tool_name="shell", arguments={"command": "ls"}, context=context2)

    # Should prompt since session2 has no permissions
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt,
    ):
        mock_prompt.return_value.prompt.return_value = "no"
        result = hook.run()
        assert not result.success
        mock_prompt.return_value.prompt.assert_called_once()


def test_fetch_permission_hook_uses_session():
    """Test that FetchPermissionHook uses session permissions."""
    session = Session.new()
    context = Context(todos=TodoManager(), history=[], session=session)
    url = "https://example.com"

    hook = FetchPermissionHook(tool_name="fetch", arguments={"url": url}, context=context)

    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt,
    ):
        mock_prompt.return_value.prompt.return_value = "always"
        result = hook.run()
        assert result.success
        assert session.permissions[f"fetch:{url}"] is True

        # Second run should not prompt
        mock_prompt.return_value.prompt.reset_mock()
        result2 = hook.run()
        assert result2.success
        mock_prompt.return_value.prompt.assert_not_called()
