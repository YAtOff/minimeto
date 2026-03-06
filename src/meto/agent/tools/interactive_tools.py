"""Interactive user operations."""

from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.enums import EditingMode
from rich.console import Console

from meto.agent.context import Context


def ask_user_question(_context: Context, question: str) -> str:
    """Ask user a question using prompt_toolkit and return response."""

    console = Console()
    session = PromptSession(editing_mode=EditingMode.EMACS)
    try:
        # Print the question with Rich formatting (prompt_toolkit doesn't interpret Rich markup)
        console.print()
        console.print(f"[bold yellow]?[/bold yellow] [bold cyan]{question}[/bold cyan]")
        console.print("[dim]Your answer:[/dim] ", end="")

        # Get input with prompt_toolkit
        response = session.prompt("")
        return response
    except (EOFError, KeyboardInterrupt):
        return "(user cancelled input)"
    except OSError as ex:
        return f"(error getting user input: {ex})"


def handle_ask_user_question(context: Context, parameters: dict[str, Any]) -> str:
    """Handle user question prompting."""
    question = parameters.get("question", "")
    return ask_user_question(context, question)
