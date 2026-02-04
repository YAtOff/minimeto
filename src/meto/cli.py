"""Command-line interface for meto"""

from __future__ import annotations

import sys
from typing import Annotated

import typer
from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode

from meto.agent.agent import Agent
from meto.agent.agent_loop import run_agent_loop
from meto.agent.exceptions import AgentInterrupted
from meto.agent.session import Session

app = typer.Typer(add_completion=False)


def _run_single_prompt(
    user_input: str,
    session: Session,
) -> None:
    """Run a single user prompt.

    Args:
        user_input: Raw user input (may be a slash command or regular prompt)
        session: Session instance for conversation history
    """
    for output in run_agent_loop(user_input, Agent.main(session)):
        print(output, flush=True)


def interactive_loop(session: Session) -> None:
    """Run interactive prompt loop with slash command and agent execution."""
    prompt_session = PromptSession(editing_mode=EditingMode.EMACS)
    while True:
        try:
            user_input = prompt_session.prompt(">>> ")
        except (EOFError, KeyboardInterrupt):
            return

        _run_single_prompt(user_input, session)


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

    session = Session(sid=session_id) if session_id else Session()

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


def main() -> None:
    app()
