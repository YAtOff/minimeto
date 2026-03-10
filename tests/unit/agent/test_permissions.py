from unittest.mock import MagicMock, patch

from meto.agent.permissions import PermissionManager
from meto.conf import settings


def _get_mock_session(yolo=False):
    session = MagicMock()
    session.permissions = {}
    session.yolo = yolo
    return session


def test_permission_manager_granted_yes():
    session = _get_mock_session()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt_session,
    ):
        mock_prompt_session.return_value.prompt.return_value = "yes"
        assert PermissionManager.check_permission("test", "Message", session) is True
        # Should not be cached
        assert "test" not in session.permissions


def test_permission_manager_granted_always():
    session = _get_mock_session()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt_session,
    ):
        mock_prompt_session.return_value.prompt.return_value = "always"
        assert PermissionManager.check_permission("test", "Message", session) is True
        # Should be cached
        assert session.permissions["test"] is True

        # Second call should not prompt
        mock_prompt_session.return_value.prompt.reset_mock()
        assert PermissionManager.check_permission("test", "Message", session) is True
        mock_prompt_session.return_value.prompt.assert_not_called()


def test_permission_manager_denied():
    session = _get_mock_session()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt_session,
    ):
        mock_prompt_session.return_value.prompt.return_value = "no"
        assert PermissionManager.check_permission("test", "Message", session) is False


def test_permission_manager_global_bypass():
    session = _get_mock_session()
    with patch.object(settings, "PERMISSIONS_ENABLED", False):
        assert PermissionManager.check_permission("test", "Message", session) is True


def test_permission_manager_yolo_bypass():
    session = _get_mock_session(yolo=True)
    with patch.object(settings, "PERMISSIONS_ENABLED", True):
        assert PermissionManager.check_permission("test", "Message", session) is True


def test_permission_manager_interrupt():
    session = _get_mock_session()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt_session,
    ):
        mock_prompt_session.return_value.prompt.side_effect = KeyboardInterrupt
        assert PermissionManager.check_permission("test", "Message", session) is False


def test_permission_manager_os_error():
    session = _get_mock_session()
    with (
        patch.object(settings, "PERMISSIONS_ENABLED", True),
        patch("meto.agent.permissions.PromptSession") as mock_prompt_session,
    ):
        mock_prompt_session.return_value.prompt.side_effect = OSError
        assert PermissionManager.check_permission("test", "Message", session) is False
