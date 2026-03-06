"""Skill and agent management."""

import json
from typing import Any

from meto.agent.context import Context
from meto.agent.exceptions import SkillAgentNotFoundError, SkillAgentValidationError
from meto.agent.loaders import get_skill_loader


def load_skill(context: Context, skill_name: str) -> str:
    """Load skill content and return it."""
    try:
        skill_loader = get_skill_loader()

        # Validate skill exists first
        if not skill_loader.has_skill(skill_name):
            available = ", ".join(skill_loader.list_skills())
            return (
                f"Error: Skill '{skill_name}' not found. Available skills: {available or '(none)'}"
            )

        # Set active skill in context
        context.active_skill = skill_name

        # Get skill content
        content = skill_loader.get_skill_content(skill_name)

        # Add hint about available agents
        agents = skill_loader.list_skill_agents(skill_name)
        if agents:
            agent_list = ", ".join(agents)
            content += f"\n\n---\n\nThis skill includes the following specialized agents (use load_agent to access them):\n{agent_list}\n"

        return content
    except ValueError as e:
        return f"Error: {e}"
    except OSError as ex:
        return f"Error: Failed to load skill '{skill_name}': {ex}"


def load_agent(context: Context, agent_name: str) -> str:
    """Load a skill-local agent configuration."""
    # Check if a skill is currently active
    if not context.active_skill:
        return "Error: No skill is currently active. Use load_skill first to load a skill, then use load_agent to access its agents."

    try:
        skill_loader = get_skill_loader()
        agent_config = skill_loader.get_skill_agent_config(context.active_skill, agent_name)

        # Return as JSON for easy parsing
        return json.dumps(agent_config, indent=2)

    except SkillAgentNotFoundError as e:
        # Provide helpful error message with available agents
        skill_loader = get_skill_loader()
        available = skill_loader.list_skill_agents(context.active_skill)
        if available:
            available_str = ", ".join(available)
            return f"Error: {e}\nAvailable agents: {available_str}"
        return f"Error: {e}"
    except SkillAgentValidationError as e:
        return f"Error: {e}"
    except Exception as ex:
        return (
            f"Error: Failed to load agent '{agent_name}' from skill '{context.active_skill}': {ex}"
        )


def handle_load_skill(context: Context, parameters: dict[str, Any]) -> str:
    """Handle skill loading."""
    skill_name = parameters.get("skill_name", "")
    return load_skill(context, skill_name)


def handle_load_agent(context: Context, parameters: dict[str, Any]) -> str:
    """Handle skill-local agent loading."""
    agent_name = parameters.get("agent_name", "")
    return load_agent(context, agent_name)
