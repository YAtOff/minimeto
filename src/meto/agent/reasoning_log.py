"""Reasoning/logging utilities.

The agent uses two logging surfaces:
- a JSONL trace file (machine-readable)
- rich-colored stderr output (human-readable)

This module keeps the logging concerns isolated from the agent loop/tool runner.
"""

import json
import logging
import random
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, override

from rich.console import Console

from meto.conf import settings

logger = logging.getLogger("agent")
logger.setLevel(logging.INFO)
logger.propagate = False


class JSONFormatter(logging.Formatter):
    """Format log records as a single-line JSON object."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "agent_name": getattr(record, "agent_name", None),
            "turn": getattr(record, "turn", None),
        }

        return json.dumps(log_obj)


@lru_cache(maxsize=1)
def reasoning_log_file() -> Path:
    """Generate actual log file path with timestamp and random suffix."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
    return settings.LOG_DIR / f"agent_reasoning_{timestamp}_{random_suffix}.jsonl"


class ReasoningLogger:
    """Structured logging for agent reasoning with JSON file + colored stderr."""

    agent_name: str
    turn_count: int
    console: Console

    _logger: logging.Logger
    _json_handler: logging.FileHandler | None

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.turn_count = 0
        self.console = Console(stderr=True)

        # Instance-specific logger to avoid accumulating handlers on a module-global logger.
        random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        self._logger = logging.getLogger(f"meto.agent.reasoning.{self.agent_name}.{random_suffix}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # Ensure we never duplicate handlers even if the same logger name is reused.
        for h in list(self._logger.handlers):
            try:
                h.close()
            finally:
                self._logger.removeHandler(h)

        self._json_handler = None

        # JSON file handler
        json_handler = logging.FileHandler(reasoning_log_file(), encoding="utf-8")
        json_handler.setFormatter(JSONFormatter())
        self._logger.addHandler(json_handler)
        self._json_handler = json_handler

    def close(self) -> None:
        """Close any file handlers attached to this logger.

        In interactive usage, ReasoningLogger instances are created frequently.
        Explicitly closing handlers prevents file descriptor leaks and duplicate logs.
        """

        for h in list(self._logger.handlers):
            try:
                h.close()
            finally:
                self._logger.removeHandler(h)
        self._json_handler = None

    def __enter__(self) -> "ReasoningLogger":
        """Support context manager protocol."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Support context manager protocol with automatic cleanup."""
        self.close()

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        """Internal log method that adds session context."""
        extra = {
            "agent_name": self.agent_name,
            **kwargs,
        }
        self._logger.log(level, msg, extra=extra)

    def log_user_input(self, prompt: str) -> None:
        """Log the incoming user prompt."""
        self._log(logging.INFO, f"User input: {prompt}")
        self.console.print(f"[bold cyan]→[/] {prompt}")

    def log_api_request(self, messages: list[dict[str, Any]]) -> None:
        """Log the messages being sent to the model."""
        self._logger.debug(f"API request with {len(messages)} messages")

    def log_model_response(self, response: Any, _model: str) -> None:
        """Log the raw model response."""
        self.turn_count += 1

        msg = response.choices[0].message
        assistant_content = msg.content or ""
        tool_calls: list[Any] = list(getattr(msg, "tool_calls", None) or [])

        self._log(logging.INFO, f"Turn {self.turn_count}: Model response", turn=self.turn_count)

        if assistant_content:
            self._log(logging.INFO, f"Assistant reasoning: {assistant_content}")
            self.console.print(f"[bold]Turn {self.turn_count}:[/] {assistant_content}")

        self._log(logging.INFO, f"Tool calls requested: {len(tool_calls)}")

        # Log token usage if available
        if hasattr(response, "usage"):
            usage = response.usage
            self._log(
                logging.INFO,
                f"Token usage - Input: {usage.prompt_tokens}({usage.prompt_tokens_details.cached_tokens}), "
                f"Output: {usage.completion_tokens}",
            )
            # Also print to console for user visibility
            self.console.print(
                f"[dim]🪙 {usage.prompt_tokens}({usage.prompt_tokens_details.cached_tokens}) ↗️, {usage.completion_tokens} ↘️[/]"
            )

    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None:
        """Log when the model selects a tool."""
        self._log(
            logging.INFO,
            f"Tool selected: {tool_name} with args: {json.dumps(arguments, indent=2)}",
        )
        args_preview = json.dumps(arguments, ensure_ascii=False)[:100]
        self.console.print(f"[dim]🔧 {tool_name} {args_preview}...[/]")

    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None:
        """Log tool execution results."""
        level = logging.ERROR if error else logging.INFO
        truncated = result[:200] + "..." if len(result) > 200 else result
        self._log(level, f"Tool '{tool_name}' result: {truncated}")

        if error:
            self.console.print(f"[red]✗ {tool_name}:[/] {truncated}")
        else:
            self.console.print(f"[green]✓ {tool_name}[/]")

    def log_reasoning(self, reasoning: str) -> None:
        """Log the model's reasoning/thinking content."""
        self._log(logging.INFO, f"Model reasoning: {reasoning}")
        self.console.print(f"[dim italic]💭 {reasoning}[/]")

    def log_skill_loaded(self, skill_name: str) -> None:
        """Log when a skill is loaded."""
        self._log(logging.INFO, f"Skill loaded: {skill_name}")
        self.console.print(f"[dim]ℹ️  Skill loaded: {skill_name}[/]")

    def log_loop_completion(self, reason: str) -> None:
        """Log why the agent loop ended."""
        self._log(
            logging.INFO,
            f"Loop completed after {self.turn_count} turns. Reason: {reason}",
        )
        self.console.print(f"[dim]Done: {reason}[/]")

    def log_system_prompt(self, system_prompt: str) -> None:
        """Log the system prompt with AGENTS.md content omitted.

        Replaces the AGENTS.md section with a simple indicator to avoid
        verbose output while showing the rest of the prompt.
        """
        begin_idx = system_prompt.find("BEGIN AGENTS.md")
        end_idx = system_prompt.find("END AGENTS.md")

        if begin_idx != -1 and end_idx != -1:
            # Find line boundaries for cleaner truncation
            begin_line_start = system_prompt.rfind("\n", 0, begin_idx) + 1
            end_line_end = system_prompt.find("\n", end_idx)

            if end_line_end == -1:
                end_line_end = len(system_prompt)

            truncated = (
                system_prompt[:begin_line_start]
                + "[AGENTS.md content omitted]\n"
                + system_prompt[end_line_end + 1 :]
            )
        else:
            truncated = system_prompt

        self._log(logging.INFO, "System prompt logged")
        self.console.print("[dim]System prompt:[/]")
        self.console.print(f"[dim]{truncated}[/]")

    def log_injected_context(self, content: str, tool_name: str | None = None) -> None:
        """Log context injected by pre-tool hooks (e.g., rule injection)."""
        tool_info = f" for {tool_name}" if tool_name else ""
        self._log(logging.INFO, f"Context injected{tool_info}: {content[:100]}...")
        self.console.print(f"[dim yellow]⚠️  Context injected{tool_info}:[/]")
        self.console.print(f"[dim yellow]{content}[/]")
