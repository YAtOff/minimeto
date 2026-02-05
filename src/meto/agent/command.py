import shlex
from typing import TYPE_CHECKING

import click
import typer

from meto.agent.history_export import dump_agent_context, format_context_summary, save_agent_context

if TYPE_CHECKING:
    from click import Context

    from meto.agent.session import Session


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


@chat_commands.command()
@click.pass_context
def help(ctx: "Context"):  # pyright: ignore[reportShadowingBuiltins]
    """Show available commands."""
    echo = click.echo
    echo(chat_commands.get_help(ctx))


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
