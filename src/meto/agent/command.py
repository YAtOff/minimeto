import json
import logging
import shlex
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

import click
import typer
from rich.console import Console
from rich.table import Table

from meto.agent.history_export import (
    dump_agent_context,
    format_context_summary,
    get_context_summary,
    save_agent_context,
)
from meto.agent.loaders.agent_loader import get_agents
from meto.agent.loaders.skill_loader import get_skill_loader
from meto.conf import settings

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from click import Context

    from meto.agent.session import Session


class NewSessionException(Exception):
    """Signal to create a new session with fresh context."""

    pass


@click.group()
@click.pass_context
def chat_commands(ctx: "Context"):
    ctx.ensure_object(dict)
    pass


@chat_commands.command()
@click.argument("path", required=False)
@click.option(
    "--format",
    type=click.Choice(["json", "pretty_json", "markdown", "text"]),
    default="json",
    help="Output format",
)
@click.option("--full", is_flag=True, help="Include system messages")
@click.pass_context
def export(ctx: "Context", path: str, format: str, full: bool):
    """Export the current context.
    Usage: /export [path] [--format json|pretty_json|markdown|text] [--full]
    """
    session = ctx.obj["session"]
    if path:
        save_agent_context(session.history, path, format, include_system=full)
    else:
        output = dump_agent_context(session.history, format, include_system=full)
        click.echo(output)


@chat_commands.command()
@click.pass_context
def context(ctx: "Context"):
    """Show current context summary."""
    session = ctx.obj["session"]
    format_context_summary(session.history)


@chat_commands.command()
@click.pass_context
def quit(ctx: "Context"):  # pyright: ignore[reportUnusedParameter]
    """Exit the REPL."""
    click.echo("Exiting...")
    raise typer.Exit(code=0)


@chat_commands.command()
@click.pass_context
def exit(ctx: "Context"):
    """Alias for quit."""
    ctx.invoke(quit)


@chat_commands.command(name="help")
@click.pass_context
def show_help(ctx: "Context"):
    """Show available commands."""
    if ctx.parent:
        click.echo(ctx.parent.get_help())
    else:
        click.echo(ctx.get_help())


@chat_commands.command()
@click.pass_context
def new(ctx: "Context"):  # pyright: ignore[reportUnusedParameter]
    """Start a new session with fresh context."""
    raise NewSessionException


@chat_commands.command()
@click.pass_context
def skills(ctx: "Context"):  # pyright: ignore[reportUnusedParameter]
    """List available skills.

    Shows all skills from both built-in and project-specific directories.
    """
    console = Console()
    loader = get_skill_loader()

    # Get all skills metadata
    all_skills = loader._resources  # pyright: ignore[reportPrivateUsage]

    if not all_skills:
        console.print("\n[yellow]No skills available.[/]")
        console.print("[dim]Skills can be added to:[/]")
        console.print("[dim]  - Project: .meto/skills/<skill-name>/SKILL.md[/]")
        console.print("[dim]  - Built-in: src/meto/resources/skills/<skill-name>/SKILL.md[/]\n")
        return

    # Determine source for each skill (built-in vs project)
    builtin_dir = (settings.DEFAULT_RESOURCES_DIR / "skills").resolve()
    project_dir = settings.SKILLS_DIR.resolve()

    table = Table(title="Available Skills", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    table.add_column("Source", style="dim")

    builtin_count = 0
    project_count = 0

    for name in sorted(all_skills.keys()):
        meta = all_skills[name]
        skill_path = meta["path"].resolve()

        # Determine source based on path
        try:
            skill_path.relative_to(builtin_dir)
            source = "built-in"
            icon = "📦"
            builtin_count += 1
        except ValueError:
            try:
                skill_path.relative_to(project_dir)
                source = "project"
                icon = "📂"
                project_count += 1
            except ValueError:
                source = "other"
                icon = "📄"
                builtin_count += 1  # Count as built-in if from resources dir

        # Truncate description if too long
        desc = meta["description"]
        if len(desc) > 60:
            desc = desc[:57] + "..."

        table.add_row(f"{icon} {name}", desc, source)

    console.print()
    console.print(table)
    console.print()

    # Summary line
    total = len(all_skills)
    parts = []
    if builtin_count > 0:
        parts.append(f"{builtin_count} built-in")
    if project_count > 0:
        parts.append(f"{project_count} project-specific")
    summary = ", ".join(parts)
    console.print(f"[dim]{total} skill{'s' if total != 1 else ''} available ({summary})[/]")
    console.print()


@chat_commands.command()
@click.pass_context
def agents(ctx: "Context"):  # pyright: ignore[reportUnusedParameter]
    """List available agents.

    Shows all agents from both built-in and project-specific directories.
    """
    console = Console()

    # Get all agents metadata
    all_agents = get_agents()

    if not all_agents:
        console.print("\n[yellow]No agents available.[/]")
        console.print("[dim]Agents can be added to:[/]")
        console.print("[dim]  - Project: .meto/agents/<agent-name>.md[/]")
        console.print("[dim]  - Built-in: src/meto/resources/agents/<agent-name>.md[/]\n")
        return

    # Determine source for each agent (built-in vs project)
    builtin_dir = (settings.DEFAULT_RESOURCES_DIR / "agents").resolve()
    project_dir = settings.AGENTS_DIR.resolve()

    table = Table(title="Available Agents", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    table.add_column("Tools", style="yellow")
    table.add_column("Source", style="dim")

    builtin_count = 0
    project_count = 0

    for name in sorted(all_agents.keys()):
        meta = all_agents[name]
        agent_path = meta["path"].resolve()

        # Determine source based on path
        try:
            agent_path.relative_to(builtin_dir)
            source = "built-in"
            icon = "📦"
            builtin_count += 1
        except ValueError:
            try:
                agent_path.relative_to(project_dir)
                source = "project"
                icon = "📂"
                project_count += 1
            except ValueError:
                source = "other"
                icon = "📄"
                builtin_count += 1  # Count as built-in if from resources dir

        # Truncate description if too long
        desc = meta["description"]
        if len(desc) > 50:
            desc = desc[:47] + "..."

        # Format tools display
        tools = meta["tools"]
        if tools == "*":
            tools_str = "* (all)"
        elif isinstance(tools, list):
            tools_str = ", ".join(tools)
            if len(tools_str) > 30:
                tools_str = ", ".join(tools[:3]) + f" (+{len(tools) - 3})"
        else:
            tools_str = str(tools)

        table.add_row(f"{icon} {name}", desc, tools_str, source)

    console.print()
    console.print(table)
    console.print()

    # Summary line
    total = len(all_agents)
    parts = []
    if builtin_count > 0:
        parts.append(f"{builtin_count} built-in")
    if project_count > 0:
        parts.append(f"{project_count} project-specific")
    summary = ", ".join(parts)
    console.print(f"[dim]{total} agent{'s' if total != 1 else ''} available ({summary})[/]")
    console.print("[dim]Use @agent <name> to run tasks with a specific agent[/]")
    console.print()


def _summarize_tool_args(args: str, max_len: int = 60) -> str:
    """Summarize tool arguments for display."""
    try:
        parsed = json.loads(args) if args else {}
        # Show only key values, truncated
        parts = []
        for k, v in list(parsed.items())[:3]:
            v_str = str(v)[:30] + ("..." if len(str(v)) > 30 else "")
            parts.append(f"{k}={v_str}")
        return ", ".join(parts)
    except (json.JSONDecodeError, TypeError):
        return args[:max_len] + ("..." if len(args) > max_len else "")


def _format_history_for_summary(
    history: Sequence[dict[str, Any]],
    max_chars: int = 15000,
) -> str:
    """Format history as readable text for LLM summarization."""
    lines = []
    total_chars = 0

    for msg in history:
        role = msg.get("role", "")
        content = str(msg.get("content", "") or "")
        entry = ""

        if role == "user":
            entry = f"USER: {content}\n"
        elif role == "assistant":
            text = content[:500] + ("..." if len(content) > 500 else "")
            entry = f"ASSISTANT: {text}\n"
            for tc in msg.get("tool_calls", []):
                fn = tc.get("function", {})
                name = fn.get("name", "unknown")
                args = _summarize_tool_args(fn.get("arguments", "{}"))
                entry += f"  TOOL: {name}({args})\n"
        elif role == "tool":
            truncated = content[:300] + ("..." if len(content) > 300 else "")
            entry = f"TOOL: {truncated}\n"

        if total_chars + len(entry) > max_chars:
            lines.append("\n[... earlier messages truncated ...]")
            break

        if entry:
            lines.append(entry)
            total_chars += len(entry)

    return "\n".join(lines)


def _generate_llm_summary(history: Sequence[dict[str, Any]]) -> str | None:
    """Generate an LLM-based semantic summary of the conversation."""
    from openai import OpenAI

    prompt = """Summarize this coding agent session concisely. Focus on:
1. **Task**: What was the user trying to accomplish?
2. **Progress**: What was completed? What remains?
3. **Key Decisions**: Any important choices made (file paths, patterns, approaches)?
4. **Context**: Files modified, commands run, errors encountered.

Output a single paragraph (max 200 words) that would help you continue this work later.

Conversation:
{conversation}"""

    conversation = _format_history_for_summary(
        history,
        max_chars=settings.COMPACT_SUMMARY_MAX_CHARS,
    )

    if len(conversation) < 100:
        return None  # Too short to summarize

    try:
        client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        response = client.chat.completions.create(
            model=settings.COMPACT_SUMMARY_MODEL,
            messages=[
                {"role": "system", "content": "You are a concise technical summarizer."},
                {"role": "user", "content": prompt.format(conversation=conversation)},
            ],
            max_tokens=300,
            temperature=0.3,
        )

        content = response.choices[0].message.content
        return content.strip() if content else None

    except Exception as e:
        logger.warning(f"LLM summarization failed: {e}")
        # Notify user of failure
        Console().print(
            f"[bold yellow]Warning:[/] AI summarization failed: {e}. Falling back to rule-based summary."
        )
        return None


def _generate_compact_summary(history: Sequence[dict[str, Any]], stats: dict[str, Any]) -> str:
    """Generate a compact summary string for logging.

    Attempts LLM-based summary first, falls back to rule-based on failure.
    """
    # Try LLM summary
    llm_summary = _generate_llm_summary(history)

    if llm_summary:
        tools = stats.get("unique_tools_used", [])
        tools_str = ", ".join(tools[:5]) + ("..." if len(tools) > 5 else "")
        return (
            f"{llm_summary}\n\n"
            f"[Stats] Messages: {stats.get('total_messages', 0)} | Tools: {tools_str}"
        )

    # Fallback to rule-based
    user_msgs = [m for m in history if m.get("role") == "user"]
    first_request = ""
    if user_msgs:
        content = user_msgs[0].get("content", "")
        first_request = content[:80] + ("..." if len(content) > 80 else "")

    tools = stats.get("unique_tools_used", [])
    tools_str = ", ".join(tools[:5]) + ("..." if len(tools) > 5 else "")

    parts = [
        f"Initial request: {first_request}" if first_request else None,
        f"Messages: {stats.get('total_messages', 0)}",
        f"Tools: {tools_str}" if tools_str else None,
    ]
    return " | ".join(p for p in parts if p)


def _display_compact_summary(stats: dict[str, Any], summary: str) -> None:
    """Display the compact summary to the user."""
    console = Console()

    console.print()
    console.print("[bold green]Session compacted[/]")
    console.print(f"[dim]{'-' * 60}[/]")
    console.print(f"[dim]Summary:[/] {summary}")
    console.print()
    console.print("[dim]Messages after compact:[/] [cyan]0[/cyan]")
    console.print(
        f"[dim]Messages preserved on disk:[/] [cyan]{stats.get('total_messages', 0)}[/cyan]"
    )
    console.print("[dim]Use /exit and restart the session to see compacted history.[/]")
    console.print(f"[dim]{'-' * 60}[/]")
    console.print()


@chat_commands.command()
@click.pass_context
def compact(ctx: "Context"):
    """Compact the session context.

    Shows a summary and logs a compact marker. When this session is
    reloaded, messages before the marker will be skipped, reducing
    memory usage while preserving full history on disk.
    """
    session = ctx.obj["session"]
    stats = get_context_summary(session.history)
    summary = _generate_compact_summary(session.history, stats)
    _display_compact_summary(stats, summary)
    session.compact(summary)


def execute_chat_command(cmdline: str, session: "Session") -> tuple[bool, str]:
    """Execute chat command with session access.

    Returns:
        (success, output)
    """
    argv = shlex.split(cmdline)
    if not argv or not argv[0].startswith("/"):
        return False, ""

    command = argv[0][1:]
    if command not in chat_commands.commands:
        return False, f"Unknown command: {command}"

    argv[0] = command
    ctx = chat_commands.make_context("chat_commands", argv)
    ctx.obj = {"session": session}

    try:
        chat_commands.invoke(ctx)
        return True, ""
    except click.exceptions.ClickException as e:
        return True, str(e)
    except typer.Exit:
        raise  # Propagate Exit to terminate REPL
    except NewSessionException:
        raise  # Propagate to create new session
