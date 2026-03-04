"""Rule loader for pre-tool context injection.

Rules are markdown files with YAML frontmatter that define coding standards
and guidelines. When a tool is about to execute, matching rules are injected
into the conversation context to guide the LLM's output.
"""

from __future__ import annotations

import fnmatch
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from meto.agent.loaders.frontmatter import parse_yaml_frontmatter
from meto.conf import settings

logger = logging.getLogger(__name__)


class RuleMetadata:
    """Metadata for a rule file."""

    name: str
    description: str
    patterns: list[str]
    path: Path
    content: str

    def __init__(
        self,
        name: str,
        description: str,
        patterns: list[str],
        path: Path,
        content: str,
    ) -> None:
        """Initialize rule metadata.

        Args:
            name: Rule name
            description: Rule description
            patterns: List of glob patterns (e.g., ["*.py", "**/*.ts"])
            path: Path to rule file
            content: Full rule content (markdown body)
        """
        self.name = name
        self.description = description
        self.patterns = patterns
        self.path = path
        self.content = content

    def matches(self, filename: str) -> bool:
        """Check if this rule matches the given filename.

        Args:
            filename: Filename to match (can include path)

        Returns:
            True if any pattern matches the filename
        """
        # Extract just the filename for pattern matching
        # This allows patterns like "*.py" to match "src/module/file.py"
        path = Path(filename)
        name_only = path.name
        relative_name = str(path)

        for pattern in self.patterns:
            # Try matching against full relative path first
            if fnmatch.fnmatch(relative_name, pattern):
                return True
            # Try matching against just the filename
            if fnmatch.fnmatch(name_only, pattern):
                return True
            # Try matching with recursive pattern support
            if pattern.startswith("**/"):
                # Remove the **/ prefix and check if any path component matches
                suffix = pattern[3:]
                if fnmatch.fnmatch(name_only, suffix):
                    return True
                # Check if the relative path ends with the suffix
                if relative_name.endswith(suffix.lstrip("*")):
                    return True

        return False


def _validate_rule_config(config: dict[str, Any]) -> list[str]:
    """Validate rule configuration.

    Args:
        config: Parsed configuration dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "description" not in config or not config["description"]:
        errors.append("Missing or empty 'description' field")
    if "description" in config and not isinstance(config["description"], str):
        errors.append("'description' must be a string")

    # Name is optional (defaults to filename without extension)
    if "name" in config and not isinstance(config["name"], str):
        errors.append("'name' must be a string")

    # Patterns are required
    if "patterns" not in config:
        errors.append("Missing 'patterns' field")
    elif "patterns" in config:
        if not isinstance(config["patterns"], list):
            errors.append("'patterns' must be a list")
        elif not config["patterns"]:
            errors.append("'patterns' cannot be empty")
        elif not all(isinstance(p, str) for p in config["patterns"]):
            errors.append("All items in 'patterns' must be strings")

    return errors


class RuleLoader:
    """Load and match rules for file operations.

    Rules are discovered at initialization and cached for performance.
    Pattern matching is performed on-demand when rules are requested.
    """

    rules_dir: Path
    _rules: list[RuleMetadata]

    def __init__(self, rules_dir: Path):
        """Initialize rule loader and discover available rules.

        Args:
            rules_dir: Path to directory containing rule files
        """
        self.rules_dir = rules_dir
        self._rules = []

        # Discover rules at initialization
        self._discover_rules()

    def _discover_rules(self) -> None:
        """Scan rules directory for .md files."""
        if not self.rules_dir.exists():
            logger.debug(f"Rules directory {self.rules_dir} does not exist, no rules loaded")
            return

        if not self.rules_dir.is_dir():
            logger.warning(f"Rules directory {self.rules_dir} is not a directory")
            return

        # Each rule is a .md file with YAML frontmatter
        for rule_file in sorted(self.rules_dir.glob("*.md")):
            if not rule_file.is_file():
                continue

            try:
                # Parse the rule file
                content = rule_file.read_text(encoding="utf-8")
                parsed = parse_yaml_frontmatter(content)
                metadata: dict[str, Any] = parsed["metadata"]  # type: ignore[assignment]
                body = parsed["body"]

                # Get name from frontmatter or filename
                name = str(metadata.get("name", rule_file.stem))
                description = str(metadata.get("description", ""))
                patterns = metadata.get("patterns", [])

                # Validate
                config = {"name": name, "description": description, "patterns": patterns}
                errors = _validate_rule_config(config)
                if errors:
                    logger.warning(f"Invalid rule {rule_file}: {', '.join(errors)}")
                    continue

                # Convert patterns to list if needed
                if not isinstance(patterns, list):
                    patterns = [patterns]

                # Store rule
                rule = RuleMetadata(
                    name=name,
                    description=description,
                    patterns=patterns,  # type: ignore[arg-type]
                    path=rule_file,
                    content=body,
                )
                self._rules.append(rule)
                logger.debug(f"Discovered rule '{name}' at {rule_file}")

            except Exception as e:
                logger.warning(f"Failed to parse rule file {rule_file}: {e}")
                continue

    def find_matching_rules(self, filename: str) -> list[RuleMetadata]:
        """Find all rules that match the given filename.

        Args:
            filename: Filename to match (can include path)

        Returns:
            List of matching rules (in discovery order)
        """
        matching = []
        for rule in self._rules:
            if rule.matches(filename):
                matching.append(rule)
        return matching

    def get_rule_content(self, rule_name: str) -> str:
        """Get the full content of a specific rule.

        Args:
            rule_name: Name of rule to load

        Returns:
            Full rule content

        Raises:
            ValueError: If rule not found
        """
        for rule in self._rules:
            if rule.name == rule_name:
                return rule.content

        available = ", ".join(sorted(r.name for r in self._rules))
        raise ValueError(f"Rule '{rule_name}' not found. Available rules: {available or '(none)'}")

    def list_rules(self) -> list[str]:
        """Return list of all available rule names.

        Returns:
            Sorted list of rule names
        """
        return sorted(rule.name for rule in self._rules)

    def get_rule_descriptions(self) -> dict[str, str]:
        """Return name->description mapping for all discovered rules.

        Returns:
            Dict mapping rule names to descriptions
        """
        return {rule.name: rule.description for rule in self._rules}

    def has_rules(self) -> bool:
        """Check if any rules are loaded.

        Returns:
            True if at least one rule is loaded, False otherwise
        """
        return len(self._rules) > 0


@lru_cache(maxsize=16)
def _get_rule_loader(rules_dir: Path | None = None) -> RuleLoader:
    """Return a cached rule loader instance.

    The cache key is the resolved rules directory path.
    """
    resolved = rules_dir if rules_dir is not None else Path(settings.RULES_DIR)
    return RuleLoader(resolved)


def get_rule_loader(rules_dir: Path | None = None) -> RuleLoader:
    """Get or create the global rule loader instance.

    Args:
        rules_dir: Directory to scan for rules

    Returns:
        RuleLoader instance
    """
    return _get_rule_loader(rules_dir)


def clear_rule_cache() -> None:
    """Clear the global rule loader cache.

    Useful for testing or when rule files change.
    """
    _get_rule_loader.cache_clear()
