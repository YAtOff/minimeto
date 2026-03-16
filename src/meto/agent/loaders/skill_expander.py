"""Skill content expansion for dynamic variables and command injection."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from meto.agent.shell import run_shell

logger = logging.getLogger(__name__)


class SkillExpander:
    """Expands dynamic tokens in skill content.

    Supports:
    - $(cmd) -> Execution of shell command and stdout injection
    - $ARGUMENTS -> Join of all provided arguments
    - $ARGUMENTS[N] -> Access to N-th argument (0-indexed)
    """

    def expand(self, content: str, arguments: Sequence[str]) -> str:
        """Perform all expansions on the given content.

        Order:
        1. $(cmd) - so that commands can potentially use $ARGUMENTS (if we decide to support that,
           but the spec says expansion happens before $ARGUMENTS expansion)
        2. $ARGUMENTS[N]
        3. $ARGUMENTS

        Args:
            content: Raw skill content (body)
            arguments: List of arguments passed to the skill

        Returns:
            Expanded content
        """
        # 1. Expand $(cmd)
        content = self._expand_commands(content)

        # 2. Expand $ARGUMENTS[N]
        content = self._expand_indexed_arguments(content, arguments)

        # 3. Expand $ARGUMENTS
        content = self._expand_all_arguments(content, arguments)

        return content

    def _expand_commands(self, content: str) -> str:
        """Expand $(cmd) tokens by executing the command."""
        pattern = r"\$\((.*?)\)"

        def _replace_cmd(match: re.Match[str]) -> str:
            cmd = match.group(1).strip()
            if not cmd:
                return ""

            logger.debug(f"Expanding skill command: {cmd}")
            # run_shell returns combined stdout/stderr, stripped
            return run_shell(cmd)

        return re.sub(pattern, _replace_cmd, content)

    def _expand_indexed_arguments(self, content: str, arguments: Sequence[str]) -> str:
        """Expand $ARGUMENTS[N] tokens."""
        pattern = r"\$ARGUMENTS\[(\d+)\]"

        def _replace_arg(match: re.Match[str]) -> str:
            try:
                index = int(match.group(1))
                if 0 <= index < len(arguments):
                    return arguments[index]
                return ""  # Out of bounds returns empty
            except (ValueError, IndexError):
                return ""

        return re.sub(pattern, _replace_arg, content)

    def _expand_all_arguments(self, content: str, arguments: Sequence[str]) -> str:
        """Expand $ARGUMENTS token with all arguments joined by spaces."""
        all_args = " ".join(arguments)
        return content.replace("$ARGUMENTS", all_args)
