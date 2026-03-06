"""Tool execution implementations.

This module contains the runtime implementations for tools exposed to the model
in :mod:`meto.agent.tool_schema`.

Architectural constraint:
    This module must not import the agent loop or CLI to avoid import cycles.
"""

# pyright: reportImportCycles=false

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from meto.agent.context import Context
from meto.agent.tools.file_tools import (
    handle_grep_search,
    handle_list_dir,
    handle_read_file,
    handle_shell,
    handle_write_file,
)
from meto.agent.tools.interactive_tools import handle_ask_user_question
from meto.agent.tools.net_tools import handle_fetch
from meto.agent.tools.registry_tools import handle_search_available_tools
from meto.agent.tools.skill_tools import handle_load_agent, handle_load_skill
from meto.agent.tools.task_tools import handle_manage_todos, handle_run_task

# Tool runtime / execution.
#
# Important architectural rule:
# - This module must not import `meto.agent.loop` or `meto.cli`.

# Type alias for tool handler functions
ToolHandler = Callable[[Context, dict[str, Any]], str]


def register_tool_handler(tool_name: str, handler: ToolHandler) -> None:
    """Register or replace a runtime tool handler."""
    _TOOL_HANDLERS[tool_name] = handler


# Log strategy: defines verbosity per tool
# - "errors_only": Only log when tool execution fails
# - "full": Log both tool selection and execution results
TOOL_LOG_STRATEGY: dict[str, str] = {
    # Log invocation with params, but skip results
    "write_file": "invocation_only",
    "fetch": "invocation_only",
    "load_skill": "invocation_only",
    "load_agent": "invocation_only",
    "list_dir": "invocation_only",
    "manage_todos": "invocation_only",
    "run_task": "invocation_only",
    # Log both invocation and results
    "read_file": "full",
    "grep_search": "full",
    # Keep existing full logging
    "shell": "full",
    "ask_user_question": "full",
    "search_available_tools": "full",
}


# Dispatch table mapping tool names to their handler functions
_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "shell": handle_shell,
    "list_dir": handle_list_dir,
    "read_file": handle_read_file,
    "write_file": handle_write_file,
    "grep_search": handle_grep_search,
    "fetch": handle_fetch,
    "ask_user_question": handle_ask_user_question,
    "manage_todos": handle_manage_todos,
    "search_available_tools": handle_search_available_tools,
    "run_task": handle_run_task,
    "load_skill": handle_load_skill,
    "load_agent": handle_load_agent,
}


def run_tool(
    context: Context,
    tool_name: str,
    parameters: dict[str, Any],
    logger: Any | None = None,
) -> str:
    """Dispatch and execute a single tool call.

    This function is the single entrypoint used by the agent loop to execute
    tools requested by the model.

    Notes:
        - The return value is always a human-readable string that is appended to
          the conversation history as a tool message.

    Args:
        context: Context object passed to tools that need it.
        tool_name: Name of the tool to execute.
        parameters: JSON-like tool arguments.
        logger: Optional reasoning logger for structured trace output.
    """
    # Get log strategy for this tool (default to "full" for unknown tools)
    log_strategy = TOOL_LOG_STRATEGY.get(tool_name, "full")

    # Log tool selection based on strategy
    strategies_with_invocation = {"full", "invocation_only"}
    if logger and log_strategy in strategies_with_invocation:
        logger.log_tool_selection(tool_name, parameters)

    tool_output = ""
    handler = _TOOL_HANDLERS.get(tool_name)

    if handler is None:
        tool_output = f"Error: Unknown tool: {tool_name}"
        # Always log unknown tool errors
        if logger:
            logger.log_tool_execution(tool_name, tool_output, error=True)
    else:
        try:
            tool_output = handler(context, parameters)
            # Log success based on strategy
            strategies_with_result = {"full", "result_only"}
            if logger and log_strategy in strategies_with_result:
                logger.log_tool_execution(tool_name, tool_output, error=False)
        except Exception as e:
            tool_output = str(e)
            # Always log errors regardless of strategy
            if logger:
                logger.log_tool_execution(tool_name, tool_output, error=True)

    return tool_output
