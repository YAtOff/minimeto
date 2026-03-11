"""Permission management for sensitive tool operations.

This module provides a session-scoped permission manager that prompts users
for confirmation before executing potentially dangerous operations.
"""

import logging

from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode

from meto.agent.session import Session
from meto.conf import settings

logger = logging.getLogger(__name__)


class PermissionManager:
    """Manages user permissions for sensitive operations during a session.

    Permissions are stored per-session (in session.permissions) to share
    state across all hook instances within a single session. This prevents
    redundant prompting (e.g., asking for shell permission multiple times
    in a single REPL session).

    The cache is preserved across the session lifetime and stored with
    the session data.
    """

    @classmethod
    def check_permission(cls, permission_key: str, message: str, session: "Session") -> bool:
        """Check if permission is granted for a given operation.

        Args:
            permission_key: Unique identifier for this permission (e.g., "shell:always")
            message: User-facing description of what needs permission
            session: The current session containing user settings and granted permissions.
                     session.yolo=True bypasses all permission checks.

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
        except OSError as e:
            logger.warning(f"Failed to get permission input: {e}")
            # Error getting input - deny permission for safety
            return False
