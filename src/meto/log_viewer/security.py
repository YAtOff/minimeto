"""Security utilities for log viewer file access.

Prevents path traversal attacks and validates filenames.
"""

from __future__ import annotations

from pathlib import Path


def validate_log_filename(filename: str) -> bool:
    """Validate that a filename is safe to use.

    Args:
        filename: The filename to validate.

    Returns:
        True if the filename is valid, False otherwise.
    """
    if not filename:
        return False

    # Reject path separators
    if "/" in filename or "\\" in filename:
        return False

    # Reject parent directory references
    if ".." in filename:
        return False

    # Require .jsonl extension
    if not filename.endswith(".jsonl"):
        return False

    return True


def safe_join_path(base_dir: Path, filename: str) -> Path | None:
    """Safely join a base directory with a filename.

    Prevents path traversal attacks by validating the filename
    and ensuring the resolved path stays within the base directory.

    Args:
        base_dir: The base directory to join from.
        filename: The filename to join.

    Returns:
        The resolved path if safe, None if the filename is invalid
        or would escape the base directory.
    """
    if not validate_log_filename(filename):
        return None

    # Resolve both paths to absolute paths
    base_resolved = base_dir.resolve()
    full_path = (base_dir / filename).resolve()

    # Ensure the resolved path is within the base directory
    try:
        full_path.relative_to(base_resolved)
    except ValueError:
        return None

    return full_path
