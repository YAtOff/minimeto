"""Command-line interface for meto"""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from rich.console import Console

from meto.agent.agent import Agent
from meto.agent.agent_loop import run_agent_loop
from meto.agent.command import execute_chat_command
from meto.agent.context import Context
from meto.agent.exceptions import AgentInterrupted
from meto.agent.mcp_client import initialize_mcp_registry
from meto.agent.session import Session
from meto.agent.syntax_expander import SyntaxExpander
from meto.agent.todo import TodoManager
from meto.agent.tool_registry import registry
from meto.conf import settings

app = typer.Typer(add_completion=False)
console = Console()


def _run_single_prompt(
    user_input: str,
    session: Session,
) -> None:
    """Run a single user prompt.

    Args:
        user_input: Raw user input (may be a slash command or regular prompt)
        session: Session instance for conversation history
    """
    # Handle slash commands
    if user_input.startswith("/"):
        success, output = execute_chat_command(user_input, session)
        if success:
            if output:
                print(output, flush=True)
            return
        # Unknown command falls through to agent

    # Normal prompt flow
    if "mcp" in settings.AGENT_FEATURES:
        warning = initialize_mcp_registry(registry)
        if warning:
            print(f"[mcp] {warning}", flush=True)

    # Try syntax expansions (@agent, ~skill, etc.)
    expander = SyntaxExpander(settings.AGENT_FEATURES)
    expanded_input, _ = expander.expand(user_input)
    agent = Agent.main()
    history = session.history
    context = Context(todos=TodoManager(), history=history)
    for output in run_agent_loop(agent, expanded_input, context):
        print(output, flush=True)


def interactive_loop(session: Session) -> None:
    """Run interactive prompt loop with slash command and agent execution."""
    prompt_session = PromptSession(editing_mode=EditingMode.EMACS)
    while True:
        try:
            user_input = prompt_session.prompt(">>> ")
        except (EOFError, KeyboardInterrupt):
            return

        try:
            _run_single_prompt(user_input, session)
        except typer.Exit:
            return


@app.callback(invoke_without_command=True)
def run(
    ctx: typer.Context,
    one_shot: Annotated[
        bool,
        typer.Option(
            "--one-shot",
            help="Read the prompt from stdin, run the agent loop with it, and exit.",
        ),
    ] = False,
    prompt: Annotated[
        str | None,
        typer.Option(
            "-p",
            "--prompt",
            help="Prompt text (only valid with --one-shot mode, stdin takes precedence)",
        ),
    ] = None,
    session_id: Annotated[
        str | None,
        typer.Option(
            "--session",
            help="Resume session by ID (format: timestamp-randomsuffix)",
        ),
    ] = None,
) -> None:
    """Run meto."""

    if ctx.invoked_subcommand is not None:
        return

    session = Session.load(session_id) if session_id else Session.new()

    if one_shot:
        # Determine input source based on precedence rules
        if prompt is not None:
            input_text = prompt.strip()
        else:
            # Read stdin once
            stdin_text = sys.stdin.read()
            input_text = stdin_text.strip()
            if not stdin_text.strip():
                raise typer.BadParameter(
                    "Either stdin or --prompt must be provided with --one-shot mode.\n"
                    "Usage: meto --one-shot [--prompt TEXT] | echo 'your prompt' | meto --one-shot",
                    param_hint="--one-shot",
                )

        # Execute the single prompt
        try:
            _run_single_prompt(input_text, session)
        except AgentInterrupted:
            print("\n[Agent interrupted]", file=sys.stderr, flush=True)
            sys.stdout.flush()
            sys.stderr.flush()
            raise typer.Exit(code=130) from None
        sys.stdout.flush()
        sys.stderr.flush()
        raise typer.Exit(code=0)

    interactive_loop(session=session)


@app.command("logs")
def logs_command(
    serve: Annotated[
        bool,
        typer.Option(
            "--serve",
            help="Start the log viewer web server",
        ),
    ] = False,
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Host to bind the server to",
        ),
    ] = "localhost",
    port: Annotated[
        int,
        typer.Option(
            "--port",
            help="Port to bind the server to",
        ),
    ] = 8000,
    no_browser: Annotated[
        bool,
        typer.Option(
            "--no-browser",
            help="Don't auto-open browser",
        ),
    ] = False,
) -> None:
    """View agent reasoning logs.

    Use --serve to start the web-based log viewer.
    """
    if serve:
        from meto.log_viewer.app import run_server

        run_server(host=host, port=port, open_browser=not no_browser)
    else:
        console.print("Use --serve to start the log viewer web server.")
        console.print("Example: meto logs --serve")
        raise typer.Exit(1)


def main() -> None:
    app()
