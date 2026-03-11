# pyright: reportUnusedImport=false

from typing import Any

from meto.agent.context import Context
from meto.agent.hooks.base import (
    ErrorResult,
    HookResult,
    InjectedResult,
    PostToolUseHook,
    PreToolUseHook,
    SuccessResult,
)

__all__ = [
    "ErrorResult",
    "HookResult",
    "InjectedResult",
    "PostToolUseHook",
    "PreToolUseHook",
    "SuccessResult",
    "post_tool_use",
    "pre_tool_use",
]


def pre_tool_use(tool_name: str, arguments: dict[str, Any], context: Context) -> HookResult:
    """Run all registered pre-tool hooks."""
    for hook_cls in PreToolUseHook.registry:
        hook_instance = hook_cls(tool_name, arguments, context)
        if hook_instance.matches():
            result = hook_instance.run()
            if not result.success or result.injected_content:
                return result
    return SuccessResult()


def post_tool_use(
    tool_name: str, arguments: dict[str, Any], output: str, context: Context
) -> HookResult:
    """Run all registered post-tool hooks."""
    for hook_cls in PostToolUseHook.registry:
        hook_instance = hook_cls(tool_name, arguments, output, context)
        if hook_instance.matches():
            result = hook_instance.run()
            if not result.success:
                return result
    return SuccessResult()


# New hooks can be added to this list to be imported and registered
from .permissions import (  # noqa: F401
    FetchPermissionHook,
    FilePermissionHook,
    ShellPermissionHook,
)
from .python_lint import PythonLintHook  # noqa: F401
from .security import SafeReadHook  # noqa: F401
