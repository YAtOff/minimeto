"""Permission management for sensitive tool operations.

This module provides a session-scoped permission manager that prompts users
for confirmation before executing potentially dangerous operations.
"""

from typing import TYPE_CHECKING

from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode

from meto.conf import settings

if TYPE_CHECKING:
    from meto.agent.session import Session


class PermissionManager:
    """Manages user permissions for sensitive operations during a session."""

    @classmethod
    def check_permission(cls, permission_key: str, message: str, session: "Session") -> bool:
        """Check if permission is granted for a given operation.

        Args:
            permission_key: Unique identifier for this permission (e.g., "shell:always")
            message: User-facing description of what needs permission
            session: The current session containing user settings and granted permissions

        Returns:
            True if permission is granted, False otherwise
        """
        # Check global bypass first, or if yolo mode is enabled in the session
        if not settings.PERMISSIONS_ENABLED or session.yolo:
            return True

        # Check cache
        if permission_key in session.permissions:
            return session.permissions[permission_key]

        # Prompt user
        prompt_session = PromptSession(editing_mode=EditingMode.EMACS)
        try:
            response = (
                prompt_session.prompt(f"[Permission Required] {message}\n(yes/no/always): ")
                .strip()
                .lower()
            )

            if response == "always":
                # Grant and cache for all future operations of this type
                session.permissions[permission_key] = True
                return True
            elif response in ("yes", "y"):
                # Grant but don't cache (ask again next time)
                return True
            else:
                # Deny
                return False

        except (EOFError, KeyboardInterrupt):
            # User cancelled - deny permission
            return False
        except OSError:
            # Error getting input - deny permission for safety
            return False
