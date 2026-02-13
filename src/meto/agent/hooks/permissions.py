"""Permission hooks for sensitive tool operations.

This module provides concrete permission hooks that integrate with the
PreToolUseHook system to request user permission before executing
potentially dangerous operations.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import override

from meto.agent.permissions import PermissionManager

from .base import HookResult, PreToolUseHook


class PermissionHook(PreToolUseHook, ABC):
    """Base class for permission-checking hooks.

    Subclasses must implement:
    - get_permission_key(): Return unique permission identifier
    - get_permission_message(): Return user-facing description
    - should_check_permission(): Return True if permission check is needed
    """

    @abstractmethod
    def get_permission_key(self) -> str:
        """Return a unique permission key for caching decisions."""
        ...

    @abstractmethod
    def get_permission_message(self) -> str:
        """Return the message to show the user when requesting permission."""
        ...

    @abstractmethod
    def should_check_permission(self) -> bool:
        """Return True if permission should be checked for this operation."""
        ...

    @override
    def run(self) -> HookResult:
        """Execute the permission check."""
        # Check if permission is needed
        if not self.should_check_permission():
            return HookResult(success=True)

        # Get permission details
        key = self.get_permission_key()
        message = self.get_permission_message()

        # Check permission via manager
        if PermissionManager.check_permission(key, message):
            return HookResult(success=True)

        # Permission denied
        return HookResult(
            success=False,
            error=f"Permission denied: {message}",
        )


class FilePermissionHook(PermissionHook):
    """Check permission before accessing files outside the current working directory."""

    matched_tools: list[str] | None = ["read_file", "write_file"]

    @override
    def get_permission_key(self) -> str:
        # Use the resolved path as the key for fine-grained control
        path = self.arguments.get("path", "")
        return f"file:outside_cwd:{Path(path).resolve()}"

    @override
    def get_permission_message(self) -> str:
        path = self.arguments.get("path", "")
        return f"Access file outside working directory: {path}"

    @override
    def should_check_permission(self) -> bool:
        """Check if file is outside current working directory."""
        path_str = self.arguments.get("path", "")
        if not path_str:
            return False

        try:
            file_path = Path(path_str).expanduser().resolve()
            cwd = Path.cwd().resolve()

            # Check if file is within CWD
            return not file_path.is_relative_to(cwd)
        except (ValueError, OSError):
            # If we can't resolve paths, err on the side of caution
            return True


class ShellPermissionHook(PermissionHook):
    """Check permission before executing shell commands."""

    matched_tools: list[str] | None = ["shell"]

    @override
    def get_permission_key(self) -> str:
        # Use a general key so "always" applies to all shell commands
        return "shell:always"

    @override
    def get_permission_message(self) -> str:
        command = self.arguments.get("command", "")
        # Truncate very long commands
        if len(command) > 100:
            command = command[:97] + "..."
        return f"Execute shell command: {command}"

    @override
    def should_check_permission(self) -> bool:
        """Always check permission for shell commands."""
        return True


class FetchPermissionHook(PermissionHook):
    """Check permission before fetching web resources."""

    matched_tools: list[str] | None = ["fetch"]

    @override
    def get_permission_key(self) -> str:
        # Use URL as key for fine-grained control
        url = self.arguments.get("url", "")
        return f"fetch:{url}"

    @override
    def get_permission_message(self) -> str:
        url = self.arguments.get("url", "")
        return f"Fetch web resource: {url}"

    @override
    def should_check_permission(self) -> bool:
        """Always check permission for web fetches."""
        return True
