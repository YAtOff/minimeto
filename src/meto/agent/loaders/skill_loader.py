"""Skill loader for on-demand domain expertise.

Skills are self-contained knowledge modules loaded reactively when needed.
Each skill is a directory containing SKILL.md with YAML frontmatter + markdown body.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

import yaml

from meto.agent.exceptions import SkillAgentNotFoundError, SkillAgentValidationError
from meto.agent.loaders.agent_loader import validate_agent_config
from meto.agent.loaders.frontmatter import parse_yaml_frontmatter
from meto.conf import settings

logger = logging.getLogger(__name__)


class SkillMetadata(TypedDict):
    """Lightweight metadata for skill discovery."""

    name: str
    description: str
    path: Path


class SkillConfig(TypedDict):
    """Full skill configuration with content."""

    name: str
    description: str
    content: str
    resources: list[str]


def _validate_skill_config(config: dict[str, Any]) -> list[str]:
    """Validate skill configuration.

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

    # Name is optional (defaults to directory name)
    if "name" in config and not isinstance(config["name"], str):
        errors.append("'name' must be a string")

    return errors


class SkillLoader:
    """Lazy-load skills: metadata at init, content on demand."""

    skills_dir: Path
    _skills: dict[str, SkillMetadata]
    _content_cache: dict[str, str]

    def __init__(self, skills_dir: Path):
        """Initialize skill loader and discover available skills.

        Args:
            skills_dir: Path to directory containing skill subdirectories
        """
        self.skills_dir = skills_dir
        self._skills = {}
        self._content_cache = {}

        # Discover skills at initialization
        self._discover_skills()

    def _discover_skills(self) -> None:
        """Scan skills directory for SKILL.md files."""
        if not self.skills_dir.exists():
            logger.debug(f"Skills directory {self.skills_dir} does not exist, no skills loaded")
            return

        if not self.skills_dir.is_dir():
            logger.warning(f"Skills directory {self.skills_dir} is not a directory")
            return

        # Each skill is a subdirectory containing SKILL.md
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue

            try:
                # Parse metadata only (lazy loading)
                content = skill_file.read_text(encoding="utf-8")
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot read skill file {skill_file}: {e}")
                continue
            except UnicodeDecodeError as e:
                logger.warning(f"Cannot decode skill file {skill_file} as UTF-8: {e}")
                continue

            try:
                parsed = parse_yaml_frontmatter(content)
                metadata: dict[str, Any] = parsed["metadata"]  # type: ignore[assignment]

                # Get name from frontmatter or directory name
                name = str(metadata.get("name", skill_dir.name))
                description = str(metadata.get("description", ""))

                # Validate
                config = {"name": name, "description": description}
                errors = _validate_skill_config(config)
                if errors:
                    logger.warning(f"Invalid skill {skill_file}: {', '.join(errors)}")
                    continue

                # Store metadata
                self._skills[name] = {
                    "name": name,
                    "description": description,
                    "path": skill_file,
                }
                logger.debug(f"Discovered skill '{name}' at {skill_file}")

            except (ValueError, KeyError) as e:
                logger.warning(f"Invalid YAML frontmatter in {skill_file}: {e}")
                continue

    def get_skill_descriptions(self) -> dict[str, str]:
        """Return name->description mapping for all discovered skills.

        Returns:
            Dict mapping skill names to descriptions
        """
        return {name: meta["description"] for name, meta in self._skills.items()}

    def get_skill_content(self, skill_name: str) -> str:
        """Load full skill content (with caching).

        Args:
            skill_name: Name of skill to load

        Returns:
            Full skill content (markdown body)

        Raises:
            ValueError: If skill not found
        """
        # Check cache first
        if skill_name in self._content_cache:
            return self._content_cache[skill_name]

        # Look up skill metadata
        if skill_name not in self._skills:
            available = ", ".join(sorted(self._skills.keys()))
            raise ValueError(
                f"Skill '{skill_name}' not found. Available skills: {available or '(none)'}"
            )

        skill_meta = self._skills[skill_name]
        skill_path = skill_meta["path"]

        try:
            # Read full file content
            content = skill_path.read_text(encoding="utf-8")
            parsed = parse_yaml_frontmatter(content)
            body = parsed["body"]

            # Check for additional resources in skill directory
            skill_dir = skill_path.parent
            resources = []
            for item in sorted(skill_dir.rglob("*")):
                if item.is_file() and item.name != "SKILL.md":
                    resources.append(str(item.relative_to(skill_dir)))

            # Build full content with resource hints
            full_content = body
            if resources:
                full_content += "\n".join(
                    (
                        "",
                        "## Additional Resources",
                        f"Base directory for this skill: `{skill_dir}`",
                        "This skill includes additional files in the same directory:",
                        "Relative paths in this skill (e.g., scripts/, reference/) are relative to this base directory.",
                        "Note: file list is sampled.",
                        "Additional files:",
                        "",
                    )
                )
                for resource in resources:
                    full_content += f"- `{skill_dir / resource}`\n"

            # Cache for future calls
            self._content_cache[skill_name] = full_content
            return full_content

        except Exception as e:
            raise ValueError(f"Failed to load skill '{skill_name}': {e}") from e

    def list_skills(self) -> list[str]:
        """Return list of all available skill names.

        Returns:
            Sorted list of skill names
        """
        return sorted(self._skills.keys())

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill exists.

        Args:
            skill_name: Name of skill to check

        Returns:
            True if skill exists, False otherwise
        """
        return skill_name in self._skills

    def get_skill_agents_dir(self, skill_name: str) -> Path | None:
        """Get the agents directory for a skill if it exists.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to agents directory, or None if it doesn't exist
        """
        if skill_name not in self._skills:
            return None

        skill_file = self._skills[skill_name]["path"]
        skill_dir = skill_file.parent
        agents_dir = skill_dir / "agents"

        if agents_dir.is_dir():
            return agents_dir
        return None

    def list_skill_agents(self, skill_name: str) -> list[str]:
        """List available agents for a specific skill.

        Args:
            skill_name: Name of the skill

        Returns:
            List of agent names (without .md extension)
        """
        agents_dir = self.get_skill_agents_dir(skill_name)
        if not agents_dir:
            return []

        agents = []
        for agent_file in sorted(agents_dir.glob("*.md")):
            if agent_file.is_file():
                agents.append(agent_file.stem)
        return agents

    def get_skill_agent_config(self, skill_name: str, agent_name: str) -> dict[str, Any]:
        """Load configuration for a skill-local agent.

        Args:
            skill_name: Name of the skill
            agent_name: Name of the agent (without .md extension)

        Returns:
            Agent configuration dict with keys: name, description, tools, prompt

        Raises:
            SkillAgentNotFoundError: If the skill or agent file doesn't exist
            SkillAgentValidationError: If the agent configuration is invalid
        """
        # Check skill exists
        if skill_name not in self._skills:
            available = ", ".join(sorted(self._skills.keys()))
            raise SkillAgentNotFoundError(
                f"Skill '{skill_name}' not found. Available skills: {available or '(none)'}"
            )

        # Get agents directory
        agents_dir = self.get_skill_agents_dir(skill_name)
        if not agents_dir:
            raise SkillAgentNotFoundError(
                f"Skill '{skill_name}' has no agents directory (expected {skill_name}/agents/)"
            )

        # Check agent file exists
        agent_file = agents_dir / f"{agent_name}.md"
        if not agent_file.is_file():
            available = ", ".join(self.list_skill_agents(skill_name))
            raise SkillAgentNotFoundError(
                f"Agent '{agent_name}' not found in skill '{skill_name}'. "
                f"Available agents: {available or '(none)'}"
            )

        # Read and parse the agent file
        try:
            content = agent_file.read_text(encoding="utf-8")
        except (PermissionError, OSError) as e:
            raise SkillAgentNotFoundError(f"Cannot read agent file {agent_file}: {e}") from e
        except UnicodeDecodeError as e:
            raise SkillAgentValidationError(
                f"Cannot decode agent file {agent_file} as UTF-8: {e}"
            ) from e

        try:
            parsed = parse_yaml_frontmatter(content)
            metadata = parsed["metadata"]
            body = parsed["body"]
        except (ValueError, KeyError, yaml.YAMLError) as e:
            raise SkillAgentValidationError(f"Invalid YAML frontmatter in {agent_file}: {e}") from e

        # Build agent config (same structure as AgentConfig)
        config = {
            "name": metadata.get("name", agent_name),
            "description": metadata.get("description", ""),
            "tools": metadata.get("tools", []),
            "prompt": metadata.get("prompt", body),
        }

        # Validate using the same validation as global agents
        errors = validate_agent_config(config)
        if errors:
            error_msg = (
                f"Agent '{agent_name}' in skill '{skill_name}' has validation errors: "
                + "; ".join(errors)
            )
            raise SkillAgentValidationError(error_msg)

        return config


@lru_cache(maxsize=16)
def _get_skill_loader(skills_dir: Path | None = None) -> SkillLoader:
    """Return a cached skill loader instance.

    The cache key is the resolved skills directory path.
    """

    resolved = skills_dir if skills_dir is not None else Path(settings.SKILLS_DIR)
    return SkillLoader(resolved)


def get_skill_loader(skills_dir: Path | None = None) -> SkillLoader:
    """Get or create the global skill loader instance.

    Args:
        skills_dir: Directory to scan for skills

    Returns:
        SkillLoader instance
    """
    return _get_skill_loader(skills_dir)


def clear_skill_cache() -> None:
    """Clear the global skill loader cache.

    Useful for testing or when skill files change.
    """
    _get_skill_loader.cache_clear()
