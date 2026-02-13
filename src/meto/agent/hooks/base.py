from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol


@dataclass(frozen=True)
class HookResult:
    success: bool
    error: str | None = None


class Hook(Protocol):
    def matches(self) -> bool: ...
    def run(self) -> HookResult: ...


class PreToolUseHook(ABC):
    """Base class for hooks that run before a tool is executed."""

    registry: ClassVar[list[type["PreToolUseHook"]]] = []
    matched_tools: list[str] | None = None

    tool_name: str
    arguments: dict[str, Any]

    def __init__(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self.tool_name = tool_name
        self.arguments = arguments

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
    output: str

    def __init__(self, tool_name: str, output: str) -> None:
        self.tool_name = tool_name
        self.output = output

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        PostToolUseHook.registry.append(cls)

    def matches(self) -> bool:
        return True

    @abstractmethod
    def run(self) -> HookResult:
        """Execute the hook logic."""
        ...
