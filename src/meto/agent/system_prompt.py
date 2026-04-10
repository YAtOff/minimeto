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
- When you need file context, read it using read_file (supports line ranges).
- For searching file contents, use grep_search with regex patterns.
- For targeted edits, use replace_text_in_file (one occurrence) or insert_in_file.
- Use write_file for creating new files or complete overwrites.
- When you need a tool you don't have, use search_available_tools first.
- Make minimal changes. Don't over-engineer.
- Keep outputs succinct; summarize what you learned.
- If a file is too large for the read_file tool, do not attempt to bypass this using `cat` or `sed`. Instead, use the read_file tool iteratively with line ranges or use grep_search to find the relevant section.

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

SKILL_AGENTS_SECTION = """Skill-local Agents (via load_agent + run_task):
- Skills can provide specialized subagents for domain-specific tasks
- Use load_agent to inspect agent configuration
- Use run_task with agent_name to execute
- Only available after loading the parent skill via load_skill
"""

HANDOVER_SECTION = """Autopilot Handover Protocol:
When you complete a task in autopilot mode, you MUST provide a standardized handover summary at the end of your final response.
Format:
### 🎯 Task Completed: [Task ID]
#### Summary: [Succinct overview of what was implemented/changed]
#### Discoveries: [Critical findings, architecture notes, or potential issues]
#### Next Steps: [Actionable advice for the next task or remaining work]
"""

RULES_SECTION = """Tool Execution Protocol: Pre-Execution Context
The system may inject relevant rules before tool execution to guide output quality.
1. Dynamic Re-evaluation: After you initiate a tool_use call, the system may provide "Additional Context" before the tool result is returned.
2. Contextual Pivot: If you receive context after a tool call but BEFORE the tool result:
   - Analyze the data: Does this new information change your parameters? (e.g., coding standards, security restrictions, or updated data)
   - Refine or Proceed: If context suggests your current tool call is suboptimal, issue a new tool call with corrected parameters.
   - If context suggests the tool is no longer needed, cancel the intent and respond directly.
   - If context is merely advisory, re-issue the same tool call to signal readiness.
3. State Management: Do not assume a tool has executed until you receive a message with role `tool`.
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
                promoted_agents = {
                    name: meta for name, meta in agents.items() if meta.get("promoted", True)
                }
                if promoted_agents:
                    agent_lines = [
                        f"- {name}: {meta['description']}"
                        for name, meta in sorted(promoted_agents.items())
                    ]
                    agents_list = "Available subagents:\n" + "\n".join(agent_lines)
                else:
                    agents_list = "Available subagents: (none promoted)"
            else:
                agents_list = "Available subagents: (none)"
            return SUBAGENTS_SECTION.format(agents_list=agents_list)
        return ""

    def render_skills(self) -> str:
        if self._is_enabled("skills"):
            loader = get_skill_loader()
            skills = loader.get_resources()
            if skills:
                promoted_skills = {
                    name: meta for name, meta in skills.items() if meta.get("promoted", True)
                }
                if promoted_skills:
                    skill_lines = [
                        f"- {name}: {meta['description']}"
                        for name, meta in sorted(promoted_skills.items())
                    ]
                    skills_list = "Available skills:\n" + "\n".join(skill_lines)
                else:
                    skills_list = "Available skills: (none promoted)"
            else:
                skills_list = "Available skills: (none)"
            return SKILLS_SECTION.format(skills_list=skills_list)
        return ""

    def render_todo_manager(self) -> str:
        if self._is_enabled("todo_manager"):
            return TODO_MANAGER_SECTION
        return ""

    def render_handover(self) -> str:
        if self._is_enabled("autopilot"):
            return HANDOVER_SECTION
        return ""

    def render_rules(self) -> str:
        if self._is_enabled("rules"):
            return RULES_SECTION
        return ""

    def build(self, agent_prompt: str) -> str:
        parts = [
            SYSTEM_PROMPT.format(cwd=os.fspath(Path.cwd())).rstrip(),
            self.render_subagents(),
            self.render_skills(),
            SKILL_AGENTS_SECTION if self._is_enabled("skills") else "",
            self.render_todo_manager(),
            self.render_handover(),
            self.render_rules(),
            self.render_agent_prompt(agent_prompt),
            self.render_agentsmd(),
        ]

        return "\n".join(filter(lambda x: bool(x), parts)) + "\n"


def build_system_prompt(agent_prompt: "str" = "", features: list[str] | None = None) -> str:
    """Build the system prompt using builder pattern.

    Args:
        agent_prompt: Optional agent-specific prompt
        features: Optional list of enabled features (defaults to settings.AGENT_FEATURES)

    Note: This re-reads AGENTS.md from disk on each call to allow live updates
    to project instructions. Other resources (subagents, skills) are cached
    within their respective loaders for performance.
    """
    if features is None:
        features = settings.AGENT_FEATURES
    return SystemPromptBuilder(features).build(agent_prompt)
