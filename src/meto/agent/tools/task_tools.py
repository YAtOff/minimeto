"""Task and todo management."""

from typing import Any, cast

from rich.console import Console
from rich.panel import Panel

from meto.agent.agent import Agent
from meto.agent.context import Context
from meto.agent.shell import truncate
from meto.conf import settings


def manage_todos(context: Context, items: list[dict[str, Any]]) -> str:
    """Update the todo list for a session.

    Args:
        context: Execution context (used to access TodoManager)
        items: List of todo items to update/add

    Returns:
        Summary of changes to the todo list
    """

    try:
        result = context.todos.update(items)
        context.todos.print_rich()
        return result
    except ValueError as e:
        return f"Error: {e}"


def execute_task(
    context: Context,
    prompt: str,
    agent_name: str,
    description: str | None = None,
) -> str:
    """Execute task in isolated subagent via direct `run_agent_loop` call.

    Args:
        context: Execution context (forked for the subagent)
        prompt: Task description/instruction for the subagent
        agent_name: Name of the agent configuration to use
        description: User-facing description of the subagent's task

    Returns:
        Final output from the subagent execution
    """

    from meto.agent.agent_loop import run_agent_loop  # pyright: ignore[reportImportCycles]

    console = Console()

    # Build banner content
    agent_line = f"[bold cyan]{agent_name}[/bold cyan]"
    if description:
        banner_content = f"{agent_line}\n[dim]{description}[/dim]"
    else:
        banner_content = agent_line

    # Show start banner
    console.print()
    console.print(
        Panel(
            banner_content,
            title="[dim]-> Starting subagent[/dim]",
            border_style="magenta",
            padding=(0, 1),
        )
    )

    # Run subagent
    try:
        # Pass active_skill context to subagent creation
        agent = Agent.subagent(agent_name, skill_name=context.active_skill)
        output = "\n".join(run_agent_loop(agent, prompt, context.fork()))
        result = truncate(output or "(subagent returned no output)", settings.MAX_TOOL_OUTPUT_CHARS)
    except Exception as ex:
        result = f"(subagent error: {ex})"

    # Show end banner
    console.print(
        Panel(
            banner_content,
            title="[dim]<- Subagent finished[/dim]",
            border_style="magenta",
            padding=(0, 1),
        )
    )
    console.print()

    return result


def handle_manage_todos(context: Context, parameters: dict[str, Any]) -> str:
    """Handle todo management."""
    items = parameters.get("items", [])
    return manage_todos(context, cast(list[dict[str, Any]], items))


def handle_run_task(context: Context, parameters: dict[str, Any]) -> str:
    """Handle subagent task execution."""
    description = cast(str, parameters.get("description", ""))
    prompt = cast(str, parameters.get("prompt", ""))
    agent_name = cast(str, parameters.get("agent_name", ""))
    return execute_task(context, prompt, agent_name, description)
