"""Base resource loader for markdown-based configurations.

Provides common logic for directory scanning, frontmatter parsing,
and validation of resource files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from meto.agent.loaders.frontmatter import parse_yaml_frontmatter

logger = logging.getLogger(__name__)


class BaseResourceLoader[T]:
    """Base class for loading resources from multiple directories.

    Handles directory validation and provides common file parsing utilities.
    Later directories override resources from earlier directories.
    """

    directories: list[Path]
    _resources: dict[str, T]
    _errors: dict[Path, str]
    _loaded: bool

    def __init__(self, directories: Path | list[Path]):
        """Initialize the loader.

        Args:
            directories: Path or list of paths to directories containing resources.
        """
        if isinstance(directories, Path):
            self.directories = [directories]
        else:
            self.directories = directories

        self._resources = {}
        self._errors = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Ensure that resources have been discovered."""
        if not self._loaded:
            self.discover()
            self._loaded = True

    def discover(self) -> None:
        """Discover resources in the directories.

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
        except (OSError, UnicodeDecodeError, ValueError, yaml.YAMLError) as e:
            msg = f"Failed to parse resource file {path}: {e}"
            logger.error(msg)
            self._errors[path] = str(e)
            return None
        except Exception as e:
            msg = f"Unexpected error parsing {path}: {e}"
            logger.error(msg, exc_info=True)
            self._errors[path] = str(e)
            raise

    def validate_directories(self) -> list[Path]:
        """Check which directories exist and are directories.

        Returns:
            List of valid directories.
        """
        valid_dirs = []
        for directory in self.directories:
            if not directory.exists():
                logger.debug(f"Directory {directory} does not exist")
                continue

            if not directory.is_dir():
                logger.warning(f"Path {directory} is not a directory")
                continue

            valid_dirs.append(directory)

        return valid_dirs

    def _report_errors(self) -> None:
        """Log a summary of errors encountered during discovery."""
        if self._errors:
            failed_count = len(self._errors)
            failed_paths = [str(p) for p in self._errors.keys()]
            logger.warning(
                f"Failed to parse {failed_count} resource files during discovery: {failed_paths}"
            )

    def clear_cache(self) -> None:
        """Clear the resource cache."""
        self._resources = {}
        self._errors = {}
        self._loaded = False

    def get_resources(self) -> dict[str, T]:
        """Return all discovered resources.

        Returns:
            Dict mapping resource names to their metadata.
        """
        self._ensure_loaded()
        return self._resources
