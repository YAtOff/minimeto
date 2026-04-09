"""Reasoning/logging utilities.

The agent uses three logging surfaces:
- a JSONL trace file (machine-readable)
- rich-colored stderr output (human-readable)
- a Markdown trace file (human-readable/archivable)

This module keeps the logging concerns isolated from the agent loop/tool runner.
"""

import json
import logging
import random
from datetime import UTC, datetime
from functools import lru_cache
from io import TextIOWrapper
from pathlib import Path
from typing import Any, Protocol, override

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


class LogWriter(Protocol):
    """Protocol for agent reasoning log writers."""

    def log_user_input(self, prompt: str) -> None: ...
    def log_api_request(self, messages: list[dict[str, Any]]) -> None: ...
    def log_model_response(self, response: Any, model: str, turn_count: int) -> None: ...
    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None: ...
    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None: ...
    def log_reasoning(self, reasoning: str) -> None: ...
    def log_skill_loaded(self, skill_name: str) -> None: ...
    def log_loop_completion(self, reason: str, turn_count: int) -> None: ...
    def log_system_prompt(self, system_prompt: str) -> None: ...
    def log_injected_context(self, content: str, tool_name: str | None = None) -> None: ...
    def close(self) -> None: ...


class ConsoleWriter:
    """Writes reasoning logs to stderr using rich."""

    console: Console

    def __init__(self) -> None:
        self.console = Console(stderr=True)

    def log_user_input(self, prompt: str) -> None:
        self.console.print(f"[bold cyan]→[/] {prompt}")

    def log_api_request(self, messages: list[dict[str, Any]]) -> None:
        _ = messages

    def log_model_response(self, response: Any, model: str, turn_count: int) -> None:
        _ = model
        msg = response.choices[0].message
        assistant_content = msg.content or ""

        if assistant_content:
            self.console.print(f"[bold]Turn {turn_count}:[/] {assistant_content}")

        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
            cached_tokens = (
                getattr(prompt_tokens_details, "cached_tokens", 0) if prompt_tokens_details else 0
            )
            self.console.print(
                f"[dim]🪙 {usage.prompt_tokens}({cached_tokens}) ↗️, {usage.completion_tokens} ↘️[/]"
            )

    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None:
        args_preview = json.dumps(arguments, ensure_ascii=False)[:100]
        self.console.print(f"[dim]🔧 {tool_name} {args_preview}...[/]")

    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None:
        truncated = result[:200] + "..." if len(result) > 200 else result
        if error:
            self.console.print(f"[red]✗ {tool_name}:[/] {truncated}")
        else:
            self.console.print(f"[green]✓ {tool_name}[/]")

    def log_reasoning(self, reasoning: str) -> None:
        self.console.print(f"[dim italic]💭 {reasoning}[/]")

    def log_skill_loaded(self, skill_name: str) -> None:
        self.console.print(f"[dim]ℹ️  Skill loaded: {skill_name}[/]")

    def log_loop_completion(self, reason: str, turn_count: int) -> None:
        _ = turn_count
        self.console.print(f"[dim]Done: {reason}[/]")

    def log_system_prompt(self, system_prompt: str) -> None:
        truncated = self._truncate_agents_md(system_prompt)
        self.console.print("[dim]System prompt:[/]")
        self.console.print(f"[dim]{truncated}[/]")

    def log_injected_context(self, content: str, tool_name: str | None = None) -> None:
        tool_info = f" for {tool_name}" if tool_name else ""
        self.console.print(f"[dim yellow]⚠️  Context injected{tool_info}:[/]")
        self.console.print(f"[dim yellow]{content}[/]")

    def _truncate_agents_md(self, system_prompt: str) -> str:
        begin_idx = system_prompt.find("BEGIN AGENTS.md")
        end_idx = system_prompt.find("END AGENTS.md")

        if begin_idx != -1 and end_idx != -1:
            begin_line_start = system_prompt.rfind("\n", 0, begin_idx) + 1
            end_line_end = system_prompt.find("\n", end_idx)
            if end_line_end == -1:
                end_line_end = len(system_prompt)

            return (
                system_prompt[:begin_line_start]
                + "[AGENTS.md content omitted]\n"
                + system_prompt[end_line_end + 1 :]
            )
        return system_prompt

    def close(self) -> None:
        pass


class JsonlWriter:
    """Writes reasoning logs to a JSONL file."""

    agent_name: str
    _logger: logging.Logger
    _json_handler: logging.FileHandler | None

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        random_suffix = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=6))
        self._logger = logging.getLogger(f"meto.agent.reasoning.{agent_name}.{random_suffix}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        # JSON file handler
        self._json_handler = logging.FileHandler(reasoning_log_file(), encoding="utf-8")
        self._json_handler.setFormatter(JSONFormatter())
        self._logger.addHandler(self._json_handler)

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        extra = {"agent_name": self.agent_name, **kwargs}
        self._logger.log(level, msg, extra=extra)

    def log_user_input(self, prompt: str) -> None:
        self._log(logging.INFO, f"User input: {prompt}")

    def log_api_request(self, messages: list[dict[str, Any]]) -> None:
        self._logger.debug(f"API request with {len(messages)} messages")

    def log_model_response(self, response: Any, model: str, turn_count: int) -> None:
        _ = model
        msg = response.choices[0].message
        assistant_content = msg.content or ""
        tool_calls = list(getattr(msg, "tool_calls", None) or [])

        self._log(logging.INFO, f"Turn {turn_count}: Model response", turn=turn_count)
        if assistant_content:
            self._log(logging.INFO, f"Assistant reasoning: {assistant_content}")

        self._log(logging.INFO, f"Tool calls requested: {len(tool_calls)}")

        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
            cached_tokens = (
                getattr(prompt_tokens_details, "cached_tokens", 0) if prompt_tokens_details else 0
            )
            self._log(
                logging.INFO,
                f"Token usage - Input: {usage.prompt_tokens}({cached_tokens}), "
                f"Output: {usage.completion_tokens}",
            )

    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None:
        self._log(
            logging.INFO,
            f"Tool selected: {tool_name} with args: {json.dumps(arguments, indent=2)}",
        )

    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None:
        level = logging.ERROR if error else logging.INFO
        truncated = result[:200] + "..." if len(result) > 200 else result
        self._log(level, f"Tool '{tool_name}' result: {truncated}")

    def log_reasoning(self, reasoning: str) -> None:
        self._log(logging.INFO, f"Model reasoning: {reasoning}")

    def log_skill_loaded(self, skill_name: str) -> None:
        self._log(logging.INFO, f"Skill loaded: {skill_name}")

    def log_loop_completion(self, reason: str, turn_count: int) -> None:
        self._log(
            logging.INFO,
            f"Loop completed after {turn_count} turns. Reason: {reason}",
        )

    def log_system_prompt(self, system_prompt: str) -> None:
        _ = system_prompt
        self._log(logging.INFO, "System prompt logged")

    def log_injected_context(self, content: str, tool_name: str | None = None) -> None:
        tool_info = f" for {tool_name}" if tool_name else ""
        self._log(logging.INFO, f"Context injected{tool_info}: {content[:100]}...")

    def close(self) -> None:
        if hasattr(self, "_json_handler") and self._json_handler:
            self._json_handler.close()
            self._logger.removeHandler(self._json_handler)
            self._json_handler = None


class MarkdownWriter:
    """Writes reasoning logs to a Markdown file."""

    md_path: Path
    file: TextIOWrapper

    def __init__(self, agent_name: str) -> None:
        jsonl_path = reasoning_log_file()
        self.md_path = jsonl_path.with_suffix(".md")
        self.file = open(self.md_path, "a", encoding="utf-8")
        self.file.write(f"# Reasoning Log - {agent_name}\n\n")
        self.file.write(f"Started at: {datetime.now(tz=UTC).isoformat()}\n\n")

    def log_user_input(self, prompt: str) -> None:
        self.file.write(f"**→** {prompt}\n\n")
        self.file.flush()

    def log_api_request(self, messages: list[dict[str, Any]]) -> None:
        _ = messages

    def log_model_response(self, response: Any, model: str, turn_count: int) -> None:
        _ = model
        msg = response.choices[0].message
        assistant_content = msg.content or ""

        self.file.write(f"### Turn {turn_count}\n\n")
        if assistant_content:
            self.file.write(f"{assistant_content}\n\n")

        if hasattr(response, "usage") and response.usage:
            usage = response.usage
            prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
            cached_tokens = (
                getattr(prompt_tokens_details, "cached_tokens", 0) if prompt_tokens_details else 0
            )
            self.file.write(
                f"*🪙 {usage.prompt_tokens}({cached_tokens}) ↗️, {usage.completion_tokens} ↘️*\n\n"
            )
        self.file.flush()

    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None:
        args_json = json.dumps(arguments, indent=2, ensure_ascii=False)
        self.file.write(f"🔧 **{tool_name}**\n\n```json\n{args_json}\n```\n\n")
        self.file.flush()

    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None:
        if error:
            self.file.write(f"❌ **{tool_name} failed**\n\n```\n{result}\n```\n\n")
        else:
            truncated = result[:500] + "..." if len(result) > 500 else result
            self.file.write(f"✅ **{tool_name} success**\n\n```\n{truncated}\n```\n\n")
        self.file.flush()

    def log_reasoning(self, reasoning: str) -> None:
        self.file.write(f"*💭 {reasoning}*\n\n")
        self.file.flush()

    def log_skill_loaded(self, skill_name: str) -> None:
        self.file.write(f"ℹ️ **Skill loaded:** {skill_name}\n\n")
        self.file.flush()

    def log_loop_completion(self, reason: str, turn_count: int) -> None:
        self.file.write(f"--- \n**Done:** {reason} (Total turns: {turn_count})\n\n")
        self.file.flush()

    def log_system_prompt(self, system_prompt: str) -> None:
        self.file.write("<details>\n<summary>System Prompt</summary>\n\n")
        self.file.write(f"```\n{system_prompt}\n```\n\n")
        self.file.write("</details>\n\n")
        self.file.flush()

    def log_injected_context(self, content: str, tool_name: str | None = None) -> None:
        tool_info = f" for {tool_name}" if tool_name else ""
        self.file.write(f"⚠️ **Context injected{tool_info}:**\n\n")
        self.file.write(f"```\n{content}\n```\n\n")
        self.file.flush()

    def close(self) -> None:
        if hasattr(self, "file") and self.file:
            self.file.close()


class ReasoningLogger:
    """Structured logging for agent reasoning using multiple writers."""

    agent_name: str
    turn_count: int
    writers: list[LogWriter]

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.turn_count = 0
        self.writers = [
            ConsoleWriter(),
            JsonlWriter(agent_name),
            MarkdownWriter(agent_name),
        ]

    def close(self) -> None:
        """Close all writers."""
        for writer in self.writers:
            writer.close()

    def __enter__(self) -> "ReasoningLogger":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def log_user_input(self, prompt: str) -> None:
        for w in self.writers:
            w.log_user_input(prompt)

    def log_api_request(self, messages: list[dict[str, Any]]) -> None:
        for w in self.writers:
            w.log_api_request(messages)

    def log_model_response(self, response: Any, model: str) -> None:
        self.turn_count += 1
        for w in self.writers:
            w.log_model_response(response, model, self.turn_count)

    def log_tool_selection(self, tool_name: str, arguments: dict[str, Any]) -> None:
        for w in self.writers:
            w.log_tool_selection(tool_name, arguments)

    def log_tool_execution(self, tool_name: str, result: str, error: bool = False) -> None:
        for w in self.writers:
            w.log_tool_execution(tool_name, result, error)

    def log_reasoning(self, reasoning: str) -> None:
        for w in self.writers:
            w.log_reasoning(reasoning)

    def log_skill_loaded(self, skill_name: str) -> None:
        for w in self.writers:
            w.log_skill_loaded(skill_name)

    def log_loop_completion(self, reason: str) -> None:
        for w in self.writers:
            w.log_loop_completion(reason, self.turn_count)

    def log_system_prompt(self, system_prompt: str) -> None:
        for w in self.writers:
            w.log_system_prompt(system_prompt)

    def log_injected_context(self, content: str, tool_name: str | None = None) -> None:
        for w in self.writers:
            w.log_injected_context(content, tool_name)
