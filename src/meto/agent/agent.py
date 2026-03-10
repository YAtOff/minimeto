"""Agent object used by the CLI and agent loop.

An Agent bundles:
- an allowed tool set (OpenAI tool schemas)
- a max turn budget for the tool-calling loop
"""

from __future__ import annotations

from typing import Any

from meto.agent.exceptions import SkillAgentNotFoundError, SubagentError
from meto.agent.loaders import get_agents
from meto.agent.loaders.skill_loader import get_skill_loader
from meto.agent.tool_registry import registry
from meto.agent.tool_schema import TOOLS
from meto.conf import settings


def get_tools_for_agent(allowed_tools: list[str] | str) -> tuple[dict[str, Any], ...]:
    """Return the list of tool schemas for the given allowlist.

    Args:
        allowed_tools: "*" or a list of tool names.

    Returns:
        List of tool schemas.
    """
    if allowed_tools == "*":
        # Start with static tools
        tools = list(TOOLS)

        # Optionally include registry tools
        if settings.INCLUDE_REGISTRY_IN_ALL_TOOLS:
            static_tool_names = {tool["function"]["name"] for tool in TOOLS}
            for registration in registry.catalog.values():
                # Avoid duplicates - static tools take precedence
                if registration.name not in static_tool_names:
                    tools.append(registration.schema)

        return tuple(tools)

    static_tools = {tool["function"]["name"]: tool for tool in TOOLS}
    resolved: list[dict[str, Any]] = []

    for tool_name in allowed_tools:
        static_tool = static_tools.get(tool_name)
        if static_tool is not None:
            resolved.append(static_tool)
            continue

        registration = registry.catalog.get(tool_name)
        if registration is not None:
            resolved.append(registration.schema)

    return tuple(resolved)


class Agent:
    """Runtime configuration for one agent execution context.

    This is intentionally a lightweight container. Most behavior lives in:
    - :func:`meto.agent.agent_loop.run_agent_loop` (LLM/tool loop)
    - :func:`meto.agent.tool_runner.run_tool` (tool execution)
    - :mod:`meto.agent.agent_registry` (agent definitions + tool selection)
    """

    name: str
    prompt: str
    tools: tuple[dict[str, Any], ...]
    max_turns: int

    @classmethod
    def main(cls) -> Agent:
        """Create the main (interactive) agent.

        The main agent:
        - has access to all tools
        """
        return cls(
            name="main",
            prompt="",
            allowed_tools="*",
            max_turns=settings.MAIN_AGENT_MAX_TURNS,
        )

    @classmethod
    def subagent(cls, name: str, skill_name: str | None = None) -> Agent:
        """Create an isolated subagent.

        Subagents run with a fresh context and a stricter
        tool allowlist defined by the agent registry.

        Args:
            name: Name of the agent to create
            skill_name: Optional skill name for skill-local agents
        """

        # If skill_name provided, try skill-local agent first
        if skill_name:
            skill_loader = get_skill_loader()
            try:
                agent_config = skill_loader.get_skill_agent_config(skill_name, name)
                return cls(
                    name=name,
                    prompt=agent_config["prompt"],
                    allowed_tools=agent_config["tools"],
                    max_turns=settings.SUBAGENT_MAX_TURNS,
                )
            except SkillAgentNotFoundError:
                # Fall through to global agents
                pass

        # Fall back to global agents
        agents = get_agents()
        agent_config = agents.get(name)

        if agent_config:
            prompt = agent_config["prompt"]
            allowed_tools = agent_config.get("tools", [])
            return cls(
                name=name,
                prompt=prompt,
                allowed_tools=allowed_tools,
                max_turns=settings.SUBAGENT_MAX_TURNS,
            )

        available = ", ".join(sorted(agents.keys()))
        raise SubagentError(f"Unknown agent type '{name}'. Available agents: {available}")

    @classmethod
    def fork(cls, allowed_tools: list[str] | str) -> Agent:
        """Create a generic subagent with an explicit tool allowlist.

        Used for custom commands that want to restrict tool access
        without creating a full agent configuration.

        Args:
            allowed_tools: Tool allowlist for the forked agent
        """

        return cls(
            name="fork",
            prompt="",
            allowed_tools=allowed_tools,
            max_turns=settings.SUBAGENT_MAX_TURNS,
        )

    def __init__(
        self,
        name: str,
        prompt: str,
        allowed_tools: list[str] | str,
        max_turns: int,
    ) -> None:
        """Create an Agent.

        Args:
            name: Agent name (e.g. "main", "explore", "plan").
            prompt: Optional extra per-agent system prompt content.
            allowed_tools: "*" or a list of tool names.
            max_turns: Max model/tool iterations per user prompt.
        """
        if max_turns <= 0:
            raise ValueError(f"max_turns must be at least 1, got {max_turns}")

        self.name = name
        self.prompt = prompt
        self.max_turns = max_turns

        self.tools = get_tools_for_agent(allowed_tools)

    @property
    def tool_names(self) -> list[str]:
        """Return the list of tool names exposed to the model."""
        return [tool["function"]["name"] for tool in self.tools]

    def has_tool(self, tool_name: str) -> bool:
        """Return True if this agent exposes the given tool name."""
        return tool_name in self.tool_names
