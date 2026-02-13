# pyright: reportUnusedImport=false

from typing import Any

from meto.agent.hooks.base import (
    HookResult,
    PostToolUseHook,
    PreToolUseHook,
)

__all__ = [
    "HookResult",
    "PostToolUseHook",
    "PreToolUseHook",
    "post_tool_use",
    "pre_tool_use",
]


def pre_tool_use(tool_name: str, arguments: dict[str, Any]) -> HookResult:
    """Run all registered pre-tool hooks."""
    for hook_cls in PreToolUseHook.registry:
        hook_instance = hook_cls(tool_name, arguments)
        if hook_instance.matches():
            result = hook_instance.run()
            if not result.success:
                return result
    return HookResult(success=True)


def post_tool_use(tool_name: str, output: str) -> HookResult:
    """Run all registered post-tool hooks."""
    for hook_cls in PostToolUseHook.registry:
        hook_instance = hook_cls(tool_name, output)
        if hook_instance.matches():
            result = hook_instance.run()
            if not result.success:
                return result
    return HookResult(success=True)


# New hooks can be added to this list to be imported and registered
from .permissions import (  # noqa: F401
    FetchPermissionHook,
    FilePermissionHook,
    ShellPermissionHook,
)
from .security import SafeReadHook  # noqa: F401
