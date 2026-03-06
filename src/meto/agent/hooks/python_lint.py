import subprocess
from typing import ClassVar, override

from meto.agent.hooks.base import HookResult, PostToolUseHook


class PythonLintHook(PostToolUseHook):
    """Hook that runs ruff lint and format after a Python file is written."""

    matched_tools: ClassVar[list[str]] = [
        "write_file",
        "replace_text_in_file",
        "insert_in_file",
    ]

    @override
    def matches(self) -> bool:
        if self.tool_name not in self.matched_tools:
            return False

        if not self.output.startswith("Successfully"):
            return False

        path = self.arguments.get("path")
        if not (isinstance(path, str) and path.endswith(".py")):
            return False

        return True

    @override
    def run(self) -> HookResult:
        path = self.arguments.get("path")
        if not path:
            return HookResult(success=True)

        try:
            # Run ruff check --fix
            # We use check=False because we don't want to fail the tool call if linting has errors
            subprocess.run(
                ["ruff", "check", "--fix", path],
                check=False,
                capture_output=True,
                text=True,
            )
            # Run ruff format
            subprocess.run(
                ["ruff", "format", path],
                check=False,
                capture_output=True,
                text=True,
            )
        except Exception:
            # Silently ignore errors in the hook itself to not disrupt the agent loop
            pass

        return HookResult(success=True)
