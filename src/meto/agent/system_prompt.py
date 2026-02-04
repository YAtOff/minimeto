"""System prompt construction.

The system prompt is built on every model call by combining:
- a static base prompt (tooling rules and capabilities)
- repository instructions from AGENTS.md

We intentionally re-read AGENTS.md each time so edits take effect immediately
without restarting the CLI.
"""

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from meto.agent.agent import Agent

# Base system prompt template.
# The final system prompt used for each model call is built by appending
# project memory/user instructions from AGENTS.md (see build_system_prompt()).
SYSTEM_PROMPT = """You are a CLI coding agent running at {cwd}.

Loop: think briefly -> use tools -> report results.

Rules:
- Prefer acting via the tools over long explanations.
- Never invent file paths. Use list_dir first if unsure.
- When you need file context, read it using read_file.
- For searching file contents, use grep_search with regex patterns.
- Make minimal changes. Don't over-engineer.
- Keep outputs succinct; summarize what you learned.
"""


def build_system_prompt(agent: "Agent | None" = None) -> str:
    """Build the system prompt.

    Appends project memory/user instructions from AGENTS.md in the current
    working directory.

    Args:
        agent: Optional agent for agent-specific prompt

    Note: This intentionally does not cache; it re-reads AGENTS.md each call.
    """

    cwd = Path.cwd()
    prompt = SYSTEM_PROMPT.format(cwd=os.fspath(cwd))

    # Allow agents to augment the prompt (e.g., planner agent instructions)
    if agent and agent.prompt:
        prompt += f"\n\n----- AGENT INSTRUCTIONS -----\n{agent.prompt}\n----- END AGENT INSTRUCTIONS -----"

    agents_path = cwd / "AGENTS.md"
    begin = "----- BEGIN AGENTS.md (project instructions) -----"
    end = "----- END AGENTS.md -----"

    try:
        agents_text = agents_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        agents_text = f"[AGENTS.md missing at: {agents_path}]"
    except OSError as e:
        agents_text = f"[AGENTS.md unreadable at: {agents_path} — {e}]"

    # Always include the delimiter block so the model reliably knows where the
    # project memory starts/ends.
    return "\n".join([prompt.rstrip(), "", begin, agents_text.rstrip(), end, ""])
