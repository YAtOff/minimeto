"""Common utilities for loading YAML frontmatter from markdown files.

Shared by agent, skill, and command loaders.
"""

from __future__ import annotations

import re
from typing import Any

import yaml

# Regex to match YAML frontmatter between --- delimiters
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


def parse_yaml_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full file content with potential frontmatter

    Returns:
        Dict with 'metadata' (parsed YAML) and 'body' (remaining content)
    """
    match = FRONTMATTER_PATTERN.match(content)
    if match:
        yaml_block, body = match.groups()
        try:
            metadata = yaml.safe_load(yaml_block) or {}
        except yaml.YAMLError as e:
            error_context = str(e)
            if hasattr(e, "problem_mark"):
                mark = e.problem_mark  # pyright: ignore[reportAttributeAccessIssue]
                # mark.line and mark.column are 0-indexed
                error_context = f"Line {mark.line + 1}, column {mark.column + 1}: {e}"
            raise ValueError(f"Invalid YAML frontmatter: {error_context}") from e

        return {"metadata": metadata, "body": body.strip()}
    else:
        # No frontmatter found, treat entire content as body
        return {"metadata": {}, "body": content.strip()}
