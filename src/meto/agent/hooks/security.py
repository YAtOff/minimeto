import fnmatch
from pathlib import Path
from typing import override

from .base import HookResult, PreToolUseHook


class SafeReadHook(PreToolUseHook):
    """
    Hook to prevent reading sensitive files like .env, private keys, or .git directory.
    """

    # Patterns for forbidden files (checked against filename and relative path)
    forbidden_patterns: list[str] = [
        ".env*",
        "*.key",
        "*.pem",
        "id_rsa*",
        "id_ed25519*",
        ".netrc",
        ".bash_history",
        ".zsh_history",
        ".history",
    ]

    # Forbidden directory names (if any part of the path matches these, it's blocked)
    forbidden_dirs: list[str] = [
        ".git",
        ".ssh",
        ".aws",
        ".config",  # Added .config as it often contains secrets
    ]

    @override
    def run(self) -> HookResult:
        path_str = self.arguments.get("path", "")
        if not path_str:
            return HookResult(success=True)

        path = Path(path_str)

        # 1. Resolve symlinks to check the real target
        try:
            # resolve() handles symlinks and returns an absolute path
            resolved_path = path.resolve()
        except (OSError, RuntimeError):
            # If resolution fails, use absolute path as fallback
            resolved_path = path.absolute()

        # 2. Check both the requested path and the resolved path
        for p in [path, resolved_path]:
            # Check directory parts
            if any(part in self.forbidden_dirs for part in p.parts):
                return HookResult(
                    success=False,
                    error=f"Blocked! Access to '{path_str}' (part of {p}) is not allowed for security reasons.",
                )

            # Check filename against patterns
            name = p.name
            for pattern in self.forbidden_patterns:
                if fnmatch.fnmatch(name, pattern):
                    return HookResult(
                        success=False,
                        error=f"Blocked! Access to '{path_str}' is not allowed for security reasons.",
                    )

        return HookResult(success=True)
