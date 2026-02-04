"""Agent object used by the CLI and agent loop.

An Agent bundles:
- a session (conversation history + todos)
- an allowed tool set (OpenAI tool schemas)
- a max turn budget for the tool-calling loop

Main agents are stateful (shared session); subagents are isolated (fresh session).
"""

from __future__ import annotations

from typing import Any

from meto.agent.exceptions import SubagentError
from meto.agent.session import NullSessionLogger, Session
from meto.agent.tool_schema import TOOLS
from meto.conf import settings


def get_tools_for_agent(allowed_tools: list[str] | str) -> list[dict[str, Any]]:
    """Return the list of tool schemas for the given allowlist.

    Args:
        allowed_tools: "*" or a list of tool names.

    Returns:
        List of tool schemas.
    """
    if allowed_tools == "*":
        return TOOLS

    allowed_set = set(allowed_tools)
    return [tool for tool in TOOLS if tool["function"]["name"] in allowed_set]


class Agent:
    """Runtime configuration for one agent execution context.

    This is intentionally a lightweight container. Most behavior lives in:
    - :func:`meto.agent.agent_loop.run_agent_loop` (LLM/tool loop)
    - :func:`meto.agent.tool_runner.run_tool` (tool execution)
    - :mod:`meto.agent.agent_registry` (agent definitions + tool selection)
    """

    name: str
    prompt: str
    session: Session
    tools: list[dict[str, Any]]
    max_turns: int

    @classmethod
    def main(cls, session: Session) -> Agent:
        """Create the main (interactive) agent.

        The main agent:
        - reuses the provided Session across prompts
        - has access to all tools
        """
        return cls(
            name="main",
            prompt="",
            session=session,
            allowed_tools="*",
            max_turns=settings.MAIN_AGENT_MAX_TURNS,
        )

    @classmethod
    def subagent(cls, name: str, parent_session: Session) -> Agent:
        """Create an isolated subagent.

        Subagents run with a fresh session (no shared history) and a stricter
        tool allowlist defined by the agent registry.

        Args:
            name: Name of the agent to create
            parent_session: Parent session
        """
        del (
            parent_session
        )  # Subagents don't share session state, so ignore this argument for now. --- IGNORE ---

        all_agents = {}
        agent_config = all_agents.get(name)

        if agent_config:
            prompt = agent_config["prompt"]
            allowed_tools = agent_config.get("tools", [])
            return cls(
                name=name,
                prompt=prompt,
                session=Session(
                    session_logger_cls=NullSessionLogger,
                ),
                allowed_tools=allowed_tools,
                max_turns=settings.SUBAGENT_MAX_TURNS,
            )

        available = ", ".join(sorted(all_agents.keys()))
        raise SubagentError(f"Unknown agent type '{name}'. Available agents: {available}")

    @classmethod
    def fork(cls, allowed_tools: list[str] | str, parent_session: Session) -> Agent:
        """Create a generic subagent with an explicit tool allowlist.

        Used for custom commands that want to restrict tool access
        without creating a full agent configuration.

        Args:
            allowed_tools: Tool allowlist for the forked agent
            parent_session: Parent session
        """
        del (
            parent_session
        )  # Subagents don't share session state, so ignore this argument for now. --- IGNORE ---

        return cls(
            name="fork",
            prompt="",
            session=Session(session_logger_cls=NullSessionLogger),
            allowed_tools=allowed_tools,
            max_turns=settings.SUBAGENT_MAX_TURNS,
        )

    def __init__(
        self,
        name: str,
        prompt: str,
        session: Session,
        allowed_tools: list[str] | str,
        max_turns: int,
    ) -> None:
        """Create an Agent.

        Args:
            name: Agent name (e.g. "main", "explore", "plan").
            prompt: Optional extra per-agent system prompt content.
            session: Conversation session (history + todos).
            allowed_tools: "*" or a list of tool names.
            max_turns: Max model/tool iterations per user prompt.
        """
        self.name = name
        self.prompt = prompt
        self.session = session
        self.max_turns = max_turns

        self.tools = get_tools_for_agent(allowed_tools)

    @property
    def tool_names(self) -> list[str]:
        """Return the list of tool names exposed to the model."""
        return [tool["function"]["name"] for tool in self.tools]

    def has_tool(self, tool_name: str) -> bool:
        """Return True if this agent exposes the given tool name."""
        return tool_name in self.tool_names
