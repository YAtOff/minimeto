"""System prompt construction.

The system prompt is built on every model call by combining:
- a static base prompt (tooling rules and capabilities)
- repository instructions from AGENTS.md

We intentionally re-read AGENTS.md each time so edits take effect immediately
without restarting the CLI.
"""

import os
from pathlib import Path

from meto.agent.loaders import get_agents, get_skill_loader
from meto.conf import settings

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
- When you need a tool you don't have, use search_available_tools first.
- Make minimal changes. Don't over-engineer.
- Keep outputs succinct; summarize what you learned.

"""

TODO_MANAGER_SECTION = """Manage multi-step tasks with todos:
- Use manage_todos to track multi-step tasks (3+ steps)
- Mark todos in_progress before starting, completed when done
- Only ONE todo can be in_progress at a time
"""

SUBAGENTS_SECTION = """Subagent pattern (via run_task tool):
- Use run_task for complex subtasks with isolated context
- Subagents run with fresh history, keep main conversation clean
{agents_list}
"""

SKILLS_SECTION = """Skills (via load_skill tool):
- On-demand domain expertise for specialized tasks
- Load skill content by name when needed
{skills_list}
"""


class SystemPromptBuilder:
    """Fluent builder for constructing system prompts."""

    def __init__(self, features: list[str]) -> None:
        self.features: set[str] = set(features)

    def _is_enabled(self, feature: str) -> bool:
        return feature in self.features

    def render_agentsmd(self) -> str:
        if self._is_enabled("agentsmd"):
            agents_path = Path.cwd() / "AGENTS.md"
            begin = "----- BEGIN AGENTS.md (project instructions) -----"
            end = "----- END AGENTS.md -----"

            try:
                agents_text = agents_path.read_text(encoding="utf-8", errors="replace")
            except FileNotFoundError:
                agents_text = f"[AGENTS.md missing at: {agents_path}]"
            except OSError as e:
                agents_text = f"[AGENTS.md unreadable at: {agents_path} — {e}]"

            return "\n".join([begin, agents_text.rstrip(), end])
        return ""

    def render_agent_prompt(self, agent_prompt: str) -> str:
        if agent_prompt:
            return "\n".join(
                [
                    "----- AGENT INSTRUCTIONS -----",
                    agent_prompt,
                    "----- END AGENT INSTRUCTIONS -----",
                ]
            )
        return ""

    def render_subagents(self) -> str:
        if self._is_enabled("subagents"):
            agents = get_agents()
            if agents:
                agent_lines = [
                    f"- {name}: {config['description']}" for name, config in agents.items()
                ]
                agents_list = "Available subagents:\n" + "\n".join(agent_lines)
            else:
                agents_list = "Available subagents: (none)"
            return SUBAGENTS_SECTION.format(agents_list=agents_list)
        return ""

    def render_skills(self) -> str:
        if self._is_enabled("skills"):
            skills = get_skill_loader().get_skill_descriptions()
            if skills:
                skill_lines = [f"- {name}: {desc}" for name, desc in sorted(skills.items())]
                skills_list = "Available skills:\n" + "\n".join(skill_lines)
            else:
                skills_list = "Available skills: (none)"
            return SKILLS_SECTION.format(skills_list=skills_list)
        return ""

    def render_todo_manager(self) -> str:
        if self._is_enabled("todo_manager"):
            return TODO_MANAGER_SECTION
        return ""

    def build(self, agent_prompt: str) -> str:
        parts = [
            SYSTEM_PROMPT.format(cwd=os.fspath(Path.cwd())).rstrip(),
            self.render_subagents(),
            self.render_skills(),
            self.render_todo_manager(),
            self.render_agent_prompt(agent_prompt),
            self.render_agentsmd(),
        ]

        return "\n".join(filter(lambda x: bool(x), parts)) + "\n"


def build_system_prompt(agent_prompt: "str" = "") -> str:
    """Build the system prompt using builder pattern.

    Args:
        agent_prompt: Optional agent-specific prompt

    Note: This intentionally does not cache; it re-reads AGENTS.md each call.
    """
    return SystemPromptBuilder(settings.AGENT_FEATURES).build(agent_prompt)
