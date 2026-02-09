from pathlib import Path
from typing import override

from .base import HookResult, PreToolUseHook


class SafeReadHook(PreToolUseHook):
    forbidden_paths: list[str] = [".env"]

    @override
    def run(self) -> HookResult:
        path = self.arguments.get("path", "")
        if Path(path).name in self.forbidden_paths:
            return HookResult(success=False, error="Blocked! Reading the file is not allowed")
        return HookResult(success=True)
