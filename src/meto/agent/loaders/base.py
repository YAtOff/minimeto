"""Base resource loader for markdown-based configurations.

Provides common logic for directory scanning, frontmatter parsing,
and validation of resource files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from meto.agent.loaders.frontmatter import parse_yaml_frontmatter

logger = logging.getLogger(__name__)


class BaseResourceLoader[T]:
    """Base class for loading resources from a directory.

    Handles directory validation and provides common file parsing utilities.
    """

    directory: Path
    _resources: dict[str, T]
    _loaded: bool

    def __init__(self, directory: Path):
        """Initialize the loader.

        Args:
            directory: Path to the directory containing resources.
        """
        self.directory = directory
        self._resources = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure that resources have been discovered."""
        if not self._loaded:
            self.discover()
            self._loaded = True

    def discover(self) -> None:
        """Discover resources in the directory.

        Should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement discover()")

    def parse_resource_file(self, path: Path) -> tuple[dict[str, Any], str] | None:
        """Parse a single markdown file with YAML frontmatter.

        Args:
            path: Path to the markdown file.

        Returns:
            Tuple of (metadata, body) if successful, None otherwise.
        """
        try:
            if not path.is_file():
                return None

            content = path.read_text(encoding="utf-8")
            parsed = parse_yaml_frontmatter(content)
            return parsed["metadata"], parsed["body"]
        except Exception as e:
            logger.warning(f"Failed to parse resource file {path}: {e}")
            return None

    def validate_directory(self) -> bool:
        """Check if the directory exists and is a directory.

        Returns:
            True if valid, False otherwise.
        """
        if not self.directory.exists():
            logger.debug(f"Directory {self.directory} does not exist")
            return False

        if not self.directory.is_dir():
            logger.warning(f"Path {self.directory} is not a directory")
            return False

        return True

    def clear_cache(self) -> None:
        """Clear the resource cache."""
        self._resources = {}
        self._loaded = False
