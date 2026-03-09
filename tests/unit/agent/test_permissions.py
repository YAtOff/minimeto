from unittest.mock import patch

from meto.agent.permissions import PermissionManager
from meto.conf import settings


def test_permission_manager_granted_yes():
    PermissionManager.reset()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_session,
    ):
        mock_session.return_value.prompt.return_value = "yes"
        assert PermissionManager.check_permission("test", "Message") is True
        # Should not be cached
        assert "test" not in PermissionManager._permissions


def test_permission_manager_granted_always():
    PermissionManager.reset()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_session,
    ):
        mock_session.return_value.prompt.return_value = "always"
        assert PermissionManager.check_permission("test", "Message") is True
        # Should be cached
        assert PermissionManager._permissions["test"] is True

        # Second call should not prompt
        mock_session.return_value.prompt.reset_mock()
        assert PermissionManager.check_permission("test", "Message") is True
        mock_session.return_value.prompt.assert_not_called()


def test_permission_manager_denied():
    PermissionManager.reset()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_session,
    ):
        mock_session.return_value.prompt.return_value = "no"
        assert PermissionManager.check_permission("test", "Message") is False


def test_permission_manager_global_bypass():
    PermissionManager.reset()
    with patch.object(settings, "PERMISSIONS_ENABLED", False):
        assert PermissionManager.check_permission("test", "Message") is True


def test_permission_manager_interrupt():
    PermissionManager.reset()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_session,
    ):
        mock_session.return_value.prompt.side_effect = KeyboardInterrupt
        assert PermissionManager.check_permission("test", "Message") is False


def test_permission_manager_os_error():
    PermissionManager.reset()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_session,
    ):
        mock_session.return_value.prompt.side_effect = OSError
        assert PermissionManager.check_permission("test", "Message") is False
