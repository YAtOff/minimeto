"""Permission management for sensitive tool operations.

This module provides a session-scoped permission manager that prompts users
for confirmation before executing potentially dangerous operations.
"""

from typing import ClassVar

from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode

from meto.conf import settings


class PermissionManager:
    """Manages user permissions for sensitive operations during a session.

    Permissions are stored at the class level to share state across all hook
    instances within a single session. This prevents redundant prompting (e.g.
    asking for shell permission multiple times in a single REPL session).

    The cache resets when the process exits.
    """

    # Class-level permission cache: {permission_key: granted}
    _permissions: ClassVar[dict[str, bool]] = {}

    @classmethod
    def check_permission(cls, permission_key: str, message: str) -> bool:
        """Check if permission is granted for a given operation.

        Args:
            permission_key: Unique identifier for this permission (e.g., "shell:always")
            message: User-facing description of what needs permission

        Returns:
            True if permission is granted, False otherwise
        """
        # Check global bypass first
        if not settings.PERMISSIONS_ENABLED:
            return True

        # Check cache
        if permission_key in cls._permissions:
            return cls._permissions[permission_key]

        # Prompt user
        session = PromptSession(editing_mode=EditingMode.EMACS)
        try:
            response = (
                session.prompt(f"[Permission Required] {message}\n(yes/no/always): ")
                .strip()
                .lower()
            )

            if response == "always":
                # Grant and cache for all future operations of this type
                cls._permissions[permission_key] = True
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

    @classmethod
    def reset(cls) -> None:
        """Reset all cached permissions. Useful for testing."""
        cls._permissions.clear()
