"""Signal handling for graceful interruption."""

import signal
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any


class InterruptSignal:
    """Simple wrapper to track interruption state."""

    def __init__(self) -> None:
        self.interrupted: bool = False

    def trigger(self) -> None:
        self.interrupted = True

    def __bool__(self) -> bool:
        return self.interrupted


@contextmanager
def handle_interrupt() -> Generator[InterruptSignal, None, None]:
    """Context manager for graceful Ctrl-C (SIGINT) interruption.

    Yields:
        InterruptSignal: An object that tracks the interruption state.
    """
    state = InterruptSignal()

    def signal_handler(_signum: int, _frame: Any) -> None:
        state.trigger()

    original_handler = signal.signal(signal.SIGINT, signal_handler)

    try:
        yield state
    finally:
        signal.signal(signal.SIGINT, original_handler)
