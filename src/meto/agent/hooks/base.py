from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from meto.agent.context import Context


@dataclass(frozen=True)
class HookResult:
    """Result of a hook execution."""

    success: bool
    error: str | None = None
    injected_content: str | None = None

    def __post_init__(self) -> None:
        if not self.success and not self.error:
            raise ValueError("HookResult with success=False must have error message")
        if self.success and self.error:
            raise ValueError("HookResult with success=True should not have error")


def SuccessResult() -> HookResult:
    """Action is allowed and nothing else is needed."""
    return HookResult(success=True)


def ErrorResult(error: str) -> HookResult:
    """Action is blocked or failed."""
    return HookResult(success=False, error=error)


def InjectedResult(injected_content: str) -> HookResult:
    """Action is allowed, but some context was injected into system prompt."""
    return HookResult(success=True, injected_content=injected_content)


class Hook(Protocol):
    def matches(self) -> bool: ...
    def run(self) -> HookResult: ...


class PreToolUseHook(ABC):
    """Base class for hooks that run before a tool is executed."""

    registry: ClassVar[list[type["PreToolUseHook"]]] = []
    matched_tools: list[str] | None = None

    tool_name: str
    arguments: dict[str, Any]
    context: "Context"

    def __init__(self, tool_name: str, arguments: dict[str, Any], context: "Context") -> None:
        self.tool_name = tool_name
        self.arguments = arguments
        self.context = context

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Skip abstract intermediary classes (those that introduce new abstract methods)
        has_new_abstract = any(
            getattr(v, "__isabstractmethod__", False) for v in cls.__dict__.values()
        )
        if not has_new_abstract:
            PreToolUseHook.registry.append(cls)

    def matches(self) -> bool:
        """Default matcher checks against matched_tools if defined."""
        if self.matched_tools is not None:
            return self.tool_name in self.matched_tools
        return True

    @abstractmethod
    def run(self) -> HookResult:
        """Execute the hook logic."""
        ...


class PostToolUseHook(ABC):
    """Base class for hooks that run after a tool is executed."""

    registry: ClassVar[list[type["PostToolUseHook"]]] = []

    tool_name: str
    arguments: dict[str, Any]
    output: str
    context: "Context"

    def __init__(self, tool_name: str, arguments: dict[str, Any], output: str, context: "Context") -> None:
        self.tool_name = tool_name
        self.arguments = arguments
        self.output = output
        self.context = context

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        PostToolUseHook.registry.append(cls)

    def matches(self) -> bool:
        return True

    @abstractmethod
    def run(self) -> HookResult:
        """Execute the hook logic."""
        ...
