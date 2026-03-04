"""Rule injection hook for pre-tool context injection.

This hook injects relevant coding rules into the conversation context
before file write/edit operations, allowing the LLM to follow project
specific guidelines. Each rule is injected only once per agent loop.
"""

from __future__ import annotations

import logging
from typing import override

from meto.agent.rule_loader import get_rule_loader
from meto.conf import settings

from .base import HookResult, PreToolUseHook

logger = logging.getLogger(__name__)


class RuleInjectionHook(PreToolUseHook):
    """Inject relevant rules before file operations.

    When a write_file or edit_file tool is called, this hook checks for
    matching rules in .meto/rules/ and injects them into the conversation
    context to guide the LLM's output.

    Each rule is injected only once per agent loop - once injected, it remains
    in the conversation context for subsequent operations.
    """

    matched_tools: list[str] | None = ["write_file", "edit_file"]

    # Class-level set to track injected rules across hook instances
    _injected_rules: set[str] = set()

    @classmethod
    def reset_injected_rules(cls) -> None:
        """Clear the set of injected rules.

        Call this at the start of each agent loop to reset tracking.
        """
        cls._injected_rules.clear()

    @override
    def run(self) -> HookResult:
        """Find and inject matching rules for the target file.

        Only injects rules that haven't been injected yet in this session.

        Returns:
            HookResult with injected_content if new rules are found
        """
        # Check if rules feature is enabled
        if "rules" not in settings.AGENT_FEATURES:
            return HookResult(success=True)

        # Extract filename from tool arguments
        # write_file uses 'path', edit_file uses 'file_path'
        filename = self.arguments.get("path") or self.arguments.get("file_path", "")
        if not filename:
            return HookResult(success=True)

        try:
            # Get matching rules
            rule_loader = get_rule_loader()
            if not rule_loader.has_rules():
                return HookResult(success=True)

            matching_rules = rule_loader.find_matching_rules(filename)
            if not matching_rules:
                return HookResult(success=True)

            # Filter out already-injected rules
            new_rules = [rule for rule in matching_rules if rule.name not in self._injected_rules]
            if not new_rules:
                # All matching rules have already been injected
                return HookResult(success=True)

            # Mark these rules as injected
            for rule in new_rules:
                self._injected_rules.add(rule.name)

            # Combine new rules only
            rule_contents = []
            for rule in new_rules:
                rule_name = rule.name
                rule_description = rule.description
                rule_content = rule.content

                rule_contents.append(f"## {rule_name}: {rule_description}\n{rule_content}")

            combined_content = "\n\n---\n\n".join(rule_contents)

            # Format injection message
            injected_message = f"""[SYSTEM INTERVENTION: PRE-TOOL CONTEXT]
The following rules apply to writing {filename}:

{combined_content}

Please ensure your {self.tool_name} operation follows these guidelines.
"""

            return HookResult(success=True, injected_content=injected_message)

        except Exception as e:
            # Log but don't block - rules are advisory
            logger.warning(f"Failed to load rules for {filename}: {e}")
            return HookResult(success=True)
