"""Skill loader for on-demand domain expertise.

Skills are self-contained knowledge modules loaded reactively when needed.
Each skill is a directory containing SKILL.md with YAML frontmatter + markdown body.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, NotRequired, TypedDict, override

from meto.agent.exceptions import SkillAgentNotFoundError, SkillAgentValidationError
from meto.agent.loaders.agent_loader import AgentLoader
from meto.agent.loaders.base import BaseResourceLoader
from meto.conf import settings

logger = logging.getLogger(__name__)


class SkillMetadata(TypedDict):
    """Lightweight metadata for skill discovery."""

    name: str
    description: str
    path: Path
    allowed_tools: NotRequired[list[str] | None]
    context: NotRequired[str | None]
    agent: NotRequired[str | None]
    model: NotRequired[str | None]
    promoted: bool


class SkillConfig(TypedDict):
    """Full skill configuration with content."""

    name: str
    description: str
    content: str
    resources: list[str]
    allowed_tools: NotRequired[list[str] | None]
    context: NotRequired[str | None]
    agent: NotRequired[str | None]
    model: NotRequired[str | None]
    promoted: bool


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

    # Optional new fields
    if "allowed_tools" in config and config["allowed_tools"] is not None:
        if not isinstance(config["allowed_tools"], list):
            errors.append("'allowed_tools' must be a list of strings")
        elif not all(isinstance(t, str) for t in config["allowed_tools"]):
            errors.append("All items in 'allowed_tools' must be strings")

    if "context" in config and config["context"] is not None:
        if not isinstance(config["context"], str):
            errors.append("'context' must be a string")

    if "agent" in config and config["agent"] is not None:
        if not isinstance(config["agent"], str):
            errors.append("'agent' must be a string")

    if "model" in config and config["model"] is not None:
        if not isinstance(config["model"], str):
            errors.append("'model' must be a string")

    if "promoted" in config and not isinstance(config["promoted"], bool):
        errors.append("'promoted' must be a boolean")

    return errors


class SkillLoader(BaseResourceLoader[SkillMetadata]):
    """Lazy-load skills: metadata at init, content on demand."""

    _content_cache: dict[str, str]

    def __init__(self, skills_dirs: Path | list[Path]):
        """Initialize skill loader and discover available skills.

        Args:
            skills_dirs: Path or list of paths to directories containing skill subdirectories
        """
        super().__init__(skills_dirs)
        self._content_cache = {}

        # Discover skills at initialization (matching original behavior)
        self.discover()

    @override
    def discover(self) -> None:
        """Scan skills directories for SKILL.md files."""
        valid_dirs = self.validate_directories()
        if not valid_dirs:
            return

        for directory in valid_dirs:
            # Each skill is a subdirectory containing SKILL.md
            for skill_dir in sorted(directory.iterdir()):
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / "SKILL.md"
                if not skill_file.is_file():
                    continue

                parsed = self.parse_resource_file(skill_file)
                if not parsed:
                    continue

                metadata, _ = parsed

                # Get name from frontmatter or directory name
                name = str(metadata.get("name", skill_dir.name))
                description = str(metadata.get("description", ""))

                # Extract new fields (with dash-to-underscore normalization)
                allowed_tools = metadata.get("allowed-tools") or metadata.get("allowed_tools")
                context = metadata.get("context")
                agent = metadata.get("agent")
                model = metadata.get("model")
                promoted = metadata.get("promoted", True)

                # Validate
                config: dict[str, Any] = {
                    "name": name,
                    "description": description,
                    "allowed_tools": allowed_tools,
                    "context": context,
                    "agent": agent,
                    "model": model,
                    "promoted": promoted,
                }
                errors = _validate_skill_config(config)
                if errors:
                    logger.warning(f"Invalid skill {skill_file}: {', '.join(errors)}")
                    continue

                # Store metadata (later directories override earlier ones)
                self._resources[name] = {
                    "name": name,
                    "description": description,
                    "path": skill_file,
                    "allowed_tools": allowed_tools,
                    "context": context,
                    "agent": agent,
                    "model": model,
                    "promoted": promoted,
                }
                logger.debug(f"Discovered skill '{name}' at {skill_file}")

        self._report_errors()

    def get_skill_descriptions(self) -> dict[str, str]:
        """Return name->description mapping for all discovered skills.

        Returns:
            Dict mapping skill names to descriptions
        """
        return {name: meta["description"] for name, meta in self._resources.items()}

    def get_skill_config(self, skill_name: str) -> SkillConfig:
        """Load full skill configuration.

        Args:
            skill_name: Name of skill to load

        Returns:
            Full skill configuration dict

        Raises:
            ValueError: If skill not found
        """
        if skill_name not in self._resources:
            available = ", ".join(sorted(self._resources.keys()))
            raise ValueError(
                f"Skill '{skill_name}' not found. Available skills: {available or '(none)'}"
            )

        skill_meta = self._resources[skill_name]
        content = self.get_skill_content(skill_name)

        # Find resources
        skill_path = skill_meta["path"]
        skill_dir = skill_path.parent
        resources = []
        for item in sorted(skill_dir.rglob("*")):
            if item.is_file() and item.name != "SKILL.md":
                resources.append(str(item.relative_to(skill_dir)))

        return {
            "name": skill_meta["name"],
            "description": skill_meta["description"],
            "content": content,
            "resources": resources,
            "allowed_tools": skill_meta.get("allowed_tools"),
            "context": skill_meta.get("context"),
            "agent": skill_meta.get("agent"),
            "model": skill_meta.get("model"),
            "promoted": skill_meta["promoted"],
        }

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
        if skill_name not in self._resources:
            available = ", ".join(sorted(self._resources.keys()))
            raise ValueError(
                f"Skill '{skill_name}' not found. Available skills: {available or '(none)'}"
            )

        skill_meta = self._resources[skill_name]
        skill_path = skill_meta["path"]

        try:
            # Read full file content
            parsed = self.parse_resource_file(skill_path)
            if not parsed:
                raise ValueError(f"Failed to parse skill file {skill_path}")

            _, body = parsed

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

        except (OSError, ValueError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to load skill '{skill_name}': {e}") from e

    def list_skills(self) -> list[str]:
        """Return list of all available skill names.

        Returns:
            Sorted list of skill names
        """
        return sorted(self._resources.keys())

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill exists.

        Args:
            skill_name: Name of skill to check

        Returns:
            True if skill exists, False otherwise
        """
        return skill_name in self._resources

    def get_skill_agents_dir(self, skill_name: str) -> Path | None:
        """Get the agents directory for a skill if it exists.

        Args:
            skill_name: Name of the skill

        Returns:
            Path to agents directory, or None if it doesn't exist
        """
        if skill_name not in self._resources:
            return None

        skill_file = self._resources[skill_name]["path"]
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
        if skill_name not in self._resources:
            available = ", ".join(sorted(self._resources.keys()))
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

        # Use AgentLoader to parse and validate the agent file
        loader = AgentLoader(agents_dir)
        config, errors = loader.validate_agent_file(agent_file)

        if errors:
            error_msg = (
                f"Agent '{agent_name}' in skill '{skill_name}' has validation errors: "
                + "; ".join(errors)
            )
            raise SkillAgentValidationError(error_msg)

        if not config:
            # Should not happen if errors is empty, but for type safety
            raise SkillAgentValidationError(
                f"Agent '{agent_name}' in skill '{skill_name}' could not be parsed."
            )

        # Merge in the name which isn't in AgentConfig but expected in the return
        return {
            "name": agent_name,
            **config,
        }

    @override
    def clear_cache(self) -> None:
        """Clear all caches."""
        super().clear_cache()
        self._content_cache = {}


@lru_cache(maxsize=16)
def _get_skill_loader(skills_dirs: tuple[Path, ...] | None = None) -> SkillLoader:
    """Return a cached skill loader instance.

    The cache key is the resolved skills directory path.
    """
    if skills_dirs is not None:
        resolved = list(skills_dirs)
    else:
        resolved = [settings.DEFAULT_RESOURCES_DIR / "skills", settings.SKILLS_DIR]

    return SkillLoader(resolved)


def get_skill_loader(skills_dirs: tuple[Path, ...] | None = None) -> SkillLoader:
    """Get or create the global skill loader instance.

    Args:
        skills_dirs: Directories to scan for skills

    Returns:
        SkillLoader instance
    """
    return _get_skill_loader(skills_dirs)


def clear_skill_cache() -> None:
    """Clear the global skill loader cache.

    Useful for testing or when skill files change.
    """
    _get_skill_loader.cache_clear()
