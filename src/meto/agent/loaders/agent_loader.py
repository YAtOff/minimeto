"""Agent type registry for subagent support.

Different agent types have different tool permissions and system prompts.
This enables context-isolated subtasks with appropriate capabilities.

Handles agent defined loading from .meto/agents/.
Supports YAML frontmatter metadata with markdown body for prompts.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict, cast

from meto.agent.exceptions import ToolNotFoundError
from meto.agent.loaders.frontmatter import parse_yaml_frontmatter
from meto.agent.tool_registry import registry
from meto.agent.tool_schema import TOOLS, TOOLS_BY_NAME
from meto.conf import settings

logger = logging.getLogger(__name__)


class AgentConfig(TypedDict):
    description: str
    tools: list[str] | str
    prompt: str


def get_tools_for_agent(requested_tools: list[str] | str) -> list[dict[str, Any]]:
    """Resolve an agent tool allowlist into concrete tool schemas.

    Args:
        requested_tools: Either "*" (all tools) or a list of tool names.

    Raises:
        ToolNotFoundError: If a named tool is not defined in the tool schema.
    """
    if requested_tools == "*":
        merged: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for tool in TOOLS:
            tool_name = cast(str, tool["function"]["name"])
            if tool_name in seen_names:
                continue
            merged.append(tool)
            seen_names.add(tool_name)

        for registration in registry.catalog.values():
            if registration.name in seen_names:
                continue
            merged.append(registration.schema)
            seen_names.add(registration.name)

        return merged

    tools_by_name = TOOLS_BY_NAME
    unknown = [
        name
        for name in requested_tools
        if name not in tools_by_name and name not in registry.catalog
    ]
    if unknown:
        known = ", ".join(sorted({*tools_by_name.keys(), *registry.catalog.keys()}))
        missing = ", ".join(unknown)
        raise ToolNotFoundError(f"Unknown tool(s): {missing}. Known tools: {known}")

    resolved: list[dict[str, Any]] = []
    for name in requested_tools:
        tool = tools_by_name.get(name)
        if tool is not None:
            resolved.append(tool)
            continue

        registration = registry.catalog.get(name)
        if registration is not None:
            resolved.append(registration.schema)

    return resolved


def validate_agent_config(config: dict[str, Any]) -> list[str]:
    """Validate agent configuration.

    Args:
        config: Parsed configuration dict

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    if "description" not in config or not config["description"]:
        errors.append("Missing or empty 'description' field")
    if not isinstance(config.get("description"), str):
        errors.append("'description' must be a string")

    # Check tools field
    if "tools" not in config:
        errors.append("Missing 'tools' field")
    else:
        tools = config["tools"]
        if tools == "*":
            pass  # All tools allowed
        elif isinstance(tools, list):
            if not tools:
                errors.append("'tools' list cannot be empty")
            for tool in tools:
                if tool not in TOOLS_BY_NAME and tool not in registry.catalog:
                    errors.append(f"Unknown tool '{tool}' in tools list")
        else:
            errors.append("'tools' must be a list or '*'")

    # Check prompt (from frontmatter or body)
    if "prompt" not in config or not config["prompt"]:
        errors.append("Missing or empty 'prompt' (must be in frontmatter or markdown body)")

    return errors


def parse_agent_file(path: Path) -> AgentConfig | None:
    """Parse a single agent file.

    Args:
        path: Path to agent markdown file

    Returns:
        AgentConfig if valid, None if parsing failed (error logged)
    """
    try:
        content = path.read_text(encoding="utf-8")
        parsed = parse_yaml_frontmatter(content)

        metadata = parsed["metadata"]
        body = parsed["body"]

        # Get name from frontmatter or filename
        name = metadata.get("name", path.stem)

        # Build config dict
        config = {
            "name": name,
            "description": metadata.get("description", ""),
            "tools": metadata.get("tools", []),
        }

        # Prompt can be in frontmatter or body
        config["prompt"] = metadata.get("prompt", body)

        # Validate
        errors = validate_agent_config(config)
        if errors:
            logger.warning(f"Invalid agent file {path}: {', '.join(errors)}")
            return None

        # Return AgentConfig
        return {
            "description": config["description"],
            "tools": config["tools"],
            "prompt": config["prompt"],
        }

    except Exception as e:
        logger.warning(f"Failed to parse agent file {path}: {e}")
        return None


class AgentLoader:
    """Lazy-load agents: agents defined in .meto/agents/."""

    agents_dir: Path
    _agents: dict[str, AgentConfig] | None

    def __init__(self, agents_dir: Path):
        """Initialize agent loader.

        Args:
            agents_dir: Path to directory containing agent files
        """
        self.agents_dir = agents_dir
        self._agents = None

    def _discover_agents(self) -> dict[str, AgentConfig]:
        """Discover and parse agent files.

        Returns:
            Dict mapping agent names to AgentConfig
        """
        if not self.agents_dir.exists():
            logger.debug(f"Agents directory {self.agents_dir} does not exist, skipping agents")
            return {}

        if not self.agents_dir.is_dir():
            logger.warning(
                f"Agents directory {self.agents_dir} is not a directory, skipping agents"
            )
            return {}

        agents: dict[str, AgentConfig] = {}

        for path in sorted(self.agents_dir.glob("*.md")):
            if path.is_file():
                agent_config = parse_agent_file(path)
                if agent_config:
                    name = path.stem
                    agents[name] = agent_config
                    logger.debug(f"Loaded agent '{name}' from {path}")

        return agents

    def _load_agents(self) -> dict[str, AgentConfig]:
        """Load agents with caching.

        Returns:
            Dict mapping agent names to AgentConfig
        """
        if self._agents is None:
            self._agents = self._discover_agents()
        return self._agents

    def get_agents(self) -> dict[str, AgentConfig]:
        """Load agents

        Returns:
            Dict mapping agent names to AgentConfig
        """
        if self._agents is not None:
            return self._agents

        self._agents = self._load_agents()
        return self._agents

    def list_agents(self) -> list[str]:
        """Return list of all available agent names.

        Returns:
            Sorted list of agent names
        """
        return sorted(self.get_agents().keys())

    def has_agent(self, agent_name: str) -> bool:
        """Check if an agent exists.

        Args:
            agent_name: Name of agent to check

        Returns:
            True if agent exists, False otherwise
        """
        return agent_name in self.get_agents()

    def get_agent_config(self, agent_name: str) -> AgentConfig:
        """Get configuration for a specific agent.

        Args:
            agent_name: Name of agent to get

        Returns:
            AgentConfig for the agent

        Raises:
            ValueError: If agent not found
        """
        agents = self.get_agents()
        if agent_name not in agents:
            available = ", ".join(sorted(agents.keys()))
            raise ValueError(
                f"Agent '{agent_name}' not found. Available agents: {available or '(none)'}"
            )
        return agents[agent_name]

    def clear_cache(self) -> None:
        """Clear all caches.

        Useful for testing or when agent files change.
        """
        self._agents = None


@lru_cache(maxsize=16)
def _get_agent_loader(agents_dir: Path | None = None) -> AgentLoader:
    """Get or create the global agent loader instance.

    Args:
        agents_dir: Directory to scan for agent files

    Returns:
        AgentLoader instance
    """
    resolved = agents_dir if agents_dir is not None else Path(settings.AGENTS_DIR)
    return AgentLoader(resolved)


def clear_agent_cache() -> None:
    """Clear the agents cache.

    Useful for testing or when agent files change.
    """
    # Reset the loader instance cache entirely.
    _get_agent_loader.cache_clear()


def get_agents(agents_dir: Path | None = None) -> dict[str, AgentConfig]:
    """Load agents

    Args:
        agents_dir: Directory to scan for agent files

    Returns:
        Dict mapping agent names to AgentConfig
    """
    loader = _get_agent_loader(agents_dir)
    return loader.get_agents()
