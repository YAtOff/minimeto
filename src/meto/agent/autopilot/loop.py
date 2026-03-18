from __future__ import annotations

import logging
import re
from collections.abc import Generator
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Table

from meto.agent.agent import Agent
from meto.agent.agent_loop import run_agent_loop
from meto.agent.autopilot.context_capsule import assemble_context_capsule
from meto.agent.autopilot.git import autopilot_commit
from meto.agent.autopilot.handover import extract_handover
from meto.agent.autopilot.models import AutopilotSession, AutopilotTask, AutopilotTaskStatus
from meto.agent.autopilot.state import AutopilotState
from meto.agent.context import Context
from meto.agent.exceptions import AgentInterrupted
from meto.conf import settings

logger = logging.getLogger(__name__)


MAX_RETRIES = 3


def run_autopilot_loop(
    goal: str,
    context: Context,
    state_file: str | Path | None = None,
    features: list[str] | None = None,
) -> Generator[str, None, None]:
    """Execute the core autopilot loop."""
    console = Console()
    state = AutopilotState(state_file)
    session = state.load()

    # Ensure autopilot feature is enabled for all agents in this loop
    if features is None:
        features = list(settings.AGENT_FEATURES)
    if "autopilot" not in features:
        features.append("autopilot")

    if not session:
        session = AutopilotSession(goal=goal)
        state.save(session)
        console.print(
            Panel(
                f"[bold green]🚀 Started new autopilot session[/]\n[dim]Goal:[/] {goal}",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[bold blue]🔄 Resumed autopilot session[/]\n[dim]Goal:[/] {session.goal}",
                border_style="blue",
            )
        )

    # Step 2: Goal decomposition
    if not session.roadmap:
        console.print("\n[bold cyan]📋 Generating roadmap...[/]")
        yield from _generate_roadmap(session, context, features=features)
        state.save(session)

    # Step 3: Sequential task execution
    while True:
        _display_roadmap(session, console)

        task = session.get_next_pending_task()
        if not task:
            console.print("\n[bold green]✅ All tasks completed![/]")
            break

        console.print(
            Panel(
                f"[bold yellow]🛠️ Working on task {task.id}[/]\n{task.description}",
                border_style="yellow",
            )
        )
        task.status = AutopilotTaskStatus.RUNNING
        session.current_task_id = task.id
        state.save(session)

        MAX_RETRIES = 3
        while task.attempts < MAX_RETRIES:
            task.attempts += 1
            if task.attempts > 1:
                console.print(
                    f"\n[yellow]🔄 Retry attempt {task.attempts}/{MAX_RETRIES} for task {task.id}...[/]"
                )

            try:
                # Fork context for isolation
                forked_context = context.fork()

                # Assemble context capsule
                sub_prompt = assemble_context_capsule(session, task)

                # Execute task with hard turn limit (Task 4.2)
                agent = Agent.subagent("code")
                # Ensure 30 turns limit
                agent = Agent(
                    name=agent.name,
                    prompt=agent.prompt,
                    allowed_tools=agent.tool_names,
                    max_turns=30,
                    model=agent.model,
                    features=features,
                )

                # Sub-task execution loop
                task_result = ""
                for chunk in run_agent_loop(agent, sub_prompt, forked_context):
                    task_result += chunk
                    yield chunk

                # Extract results
                handover = extract_handover(task_result)
                task.status = AutopilotTaskStatus.COMPLETED
                task.handover = handover
                task.error = None

                # Git commit after success
                autopilot_commit(task)
                console.print(f"\n[dim]💾 Committed changes for task {task.id}[/]")

                # Success, break the retry loop
                break

            except (AgentInterrupted, KeyboardInterrupt):
                logger.info(f"Task {task.id} interrupted by user")
                task.status = AutopilotTaskStatus.FAILED
                task.error = "Interrupted by user"
                console.print(f"\n[bold yellow]⚠️ Task {task.id} interrupted by user[/]")
                raise  # Re-raise to stop autopilot
            except Exception as e:
                logger.error(f"Task {task.id} attempt {task.attempts} failed: {e}", exc_info=True)
                task.error = str(e)
                if task.attempts >= MAX_RETRIES:
                    task.status = AutopilotTaskStatus.FAILED
                    console.print(
                        f"\n[bold red]❌ Task {task.id} failed after {MAX_RETRIES} attempts: {e}[/]"
                    )
                    break
                console.print(f"\n[yellow]⚠️ Attempt {task.attempts} failed: {e}. Retrying...[/]")
            finally:
                state.save(session)

        if task.status != AutopilotTaskStatus.COMPLETED:
            console.print(
                "\n[bold red]⛔ Autopilot paused due to task failure. Please resolve manually and resume.[/]"
            )
            break

        session.current_task_id = None
        state.save(session)

    _display_summary(session, console)


def _display_roadmap(session: AutopilotSession, console: Console) -> None:
    """Display the current roadmap and progress."""
    table = Table(
        title="Autopilot Roadmap", show_header=True, header_style="bold cyan", expand=True
    )
    table.add_column("ID", style="dim", width=5)
    table.add_column("Status", width=12)
    table.add_column("Description")

    for task in session.roadmap:
        status_style = {
            AutopilotTaskStatus.PENDING: "white",
            AutopilotTaskStatus.RUNNING: "bold yellow",
            AutopilotTaskStatus.COMPLETED: "green",
            AutopilotTaskStatus.FAILED: "bold red",
        }.get(task.status, "white")

        status_icon = {
            AutopilotTaskStatus.PENDING: "○",
            AutopilotTaskStatus.RUNNING: "▶",
            AutopilotTaskStatus.COMPLETED: "✓",
            AutopilotTaskStatus.FAILED: "✗",
        }.get(task.status, "?")

        table.add_row(
            task.id,
            f"[{status_style}]{status_icon} {task.status.value.upper()}[/]",
            task.description,
        )

    console.print()
    console.print(table)

    # Progress bar
    completed, total = session.progress
    if total > 0:
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total} tasks)"),
            console=console,
        )
        with progress:
            progress.add_task("[cyan]Overall Progress", total=total, completed=completed)
    console.print()


def _display_summary(session: AutopilotSession, console: Console) -> None:
    """Display the final session summary."""
    completed, total = session.progress
    color = "green" if completed == total else "yellow"

    summary_text = f"Progress: {completed}/{total} tasks complete."
    if completed == total:
        summary_text += "\n[bold]All objectives achieved![/]"
    else:
        summary_text += f"\n[bold]Paused at task {session.current_task_id or '?'}.[/]"

    console.print(Panel(summary_text, title="🏁 Autopilot Summary", border_style=color))


def _generate_roadmap(
    session: AutopilotSession, context: Context, features: list[str] | None = None
) -> Generator[str, None, None]:
    """Call the planner agent to create a roadmap and parse the results."""
    planner = Agent.subagent("plan")
    if features:
        planner.features = features
    prompt = (
        f"Goal: {session.goal}\n\n"
        "Please create a comprehensive implementation plan. "
        "At the end, include a structured AUTOPILOT_ROADMAP block with the following format:\n"
        "### 🚀 AUTOPILOT_ROADMAP\n"
        "### 🎯 Task: ID | Description\n"
        "### 🎯 Task: ID | Description\n"
    )

    full_output = ""
    for chunk in run_agent_loop(planner, prompt, context.fork()):
        full_output += chunk
        yield chunk

    # Parse roadmap from output
    roadmap = []
    task_pattern = re.compile(r"### \U0001F3AF Task:\s*(?P<id>[^|]+)\|\s*(?P<desc>.+)")

    for match in task_pattern.finditer(full_output):
        task_id = match.group("id").strip()
        description = match.group("desc").strip()
        roadmap.append(AutopilotTask(id=task_id, description=description))

    if not roadmap:
        logger.error(
            f"Failed to parse roadmap from planner output. "
            f"Output length: {len(full_output)} chars. "
            f"Pattern: {task_pattern.pattern}"
        )
        yield (
            "\n[bold red]❌ Autopilot Error:[/] No structured roadmap found in planner output.\n"
            "The planner agent must include a AUTOPILOT_ROADMAP block with tasks formatted as:\n"
            "### 🎯 Task: ID | Description\n\n"
            "Please check the planner output above for errors and adjust your goal or planner agent.\n"
        )
        raise RuntimeError("Failed to parse roadmap from planner output")

    session.roadmap = roadmap
    yield f"\n✅ Roadmap generated with {len(roadmap)} tasks.\n"
