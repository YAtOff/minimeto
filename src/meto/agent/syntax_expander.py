"""Syntax expansion for shorthand notations (@agent, ~skill, etc.)."""

from __future__ import annotations

import re

from meto.agent.loaders import get_agents
from meto.agent.loaders.skill_loader import get_skill_loader


class SyntaxExpander:
    """Expands shorthand syntax to explicit tool instructions.

    Supports:
    - @agent task -> run_task tool with agent_name
    - ~skill task -> load_skill tool with skill_name
    """

    _features: set[str]

    def __init__(self, features: list[str]) -> None:
        """Initialize expander with available features.

        Args:
            features: List of enabled feature names from settings.AGENT_FEATURES
        """
        self._features = set(features)

    def expand(self, user_input: str) -> tuple[str, bool]:
        """Try all expansions in priority order.

        Args:
            user_input: Raw user input

        Returns:
            (expanded_prompt, was_expanded)
        """
        expansions = [
            self._expand_agent_syntax,
            self._expand_skill_syntax,
        ]

        for expander in expansions:
            result, was_expanded = expander(user_input)
            if was_expanded:
                return result, True

        return user_input, False

    def _expand_agent_syntax(self, user_input: str) -> tuple[str, bool]:
        """Expand @agent syntax to explicit run_task instructions.

        Only expands if:
        - subagents feature is enabled
        - the agent exists

        Args:
            user_input: Raw user input

        Returns:
            (expanded_prompt, was_expanded)
        """
        if "subagents" not in self._features:
            return user_input, False

        pattern = r"@(\w+)\s+(.+)"
        match = re.match(pattern, user_input.strip())
        if not match:
            return user_input, False

        agent_name = match.group(1)
        task = match.group(2)

        # Check if agent exists
        agents = get_agents()
        if agent_name not in agents:
            return user_input, False

        expanded = f"Use run_task tool with agent_name='{agent_name}' to: {task}"
        return expanded, True

    def _expand_skill_syntax(self, user_input: str) -> tuple[str, bool]:
        """Expand ~skill syntax to explicit load_skill instructions.

        Only expands if:
        - skills feature is enabled
        - the skill exists

        Args:
            user_input: Raw user input

        Returns:
            (expanded_prompt, was_expanded)
        """
        if "skills" not in self._features:
            return user_input, False

        pattern = r"~(\w+)\s+(.+)"
        match = re.match(pattern, user_input.strip())
        if not match:
            return user_input, False

        skill_name = match.group(1)
        task = match.group(2)

        # Check if skill exists
        skill_loader = get_skill_loader()
        if not skill_loader.has_skill(skill_name):
            return user_input, False

        expanded = (
            f"Use load_skill tool with skill_name='{skill_name}' to gain expertise. Then: {task}"
        )
        return expanded, True
