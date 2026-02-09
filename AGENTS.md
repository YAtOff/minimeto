# AGENTS.md

This file provides guidance to Meto when working with code in this repository.

## Common Commands

```bash
# Full workflow (install + lint + test)
just

# Individual commands
just install      # uv sync --all-extras
just lint         # ruff format + check + basedpyright
just test         # pytest
just build        # uv build
just clean        # remove build artifacts

# Direct uv commands
uv run pytest                    # run tests
uv run python devtools/lint.py   # lint
uv build                         # build wheel
uv run meto                      # run the agent REPL
```

## Project Philosophy

**Multiple tools + ONE loop (tool-calling) = capable coding agent**

This is a minimal coding agent that achieves power through simplicity: an LLM with access to various tools running in a continuous loop until task completion.

## Architecture

### Core Components

- **[cli.py](src/meto/cli.py)** - CLI interface with Typer. Supports interactive REPL (`uv run meto`) and one-shot mode (`uv run meto --one-shot`)
- **[agent/agent_loop.py](src/meto/agent/agent_loop.py)** - The heart: tool-calling loop that executes LLM responses
- **[agent/agent.py](src/meto/agent/agent.py)** - Agent factory creating main agents and subagents with different tool permissions
- **[agent/tool_runner.py](src/meto/agent/tool_runner.py)** - Tool implementations (shell, read, write, edit, grep, web_fetch, etc.)
- **[agent/tool_schema.py](src/meto/agent/tool_schema.py)** - OpenAI-compatible tool schemas
- **[agent/session.py](src/meto/agent/session.py)** - Conversation history and state management
- **[agent/context.py](src/meto/agent/context.py)** - Context object passed to tools (todos, history)
- **[agent/system_prompt.py](src/meto/agent/system_prompt.py)** - System prompt builder with feature flags
- **[agent/syntax_expander.py](src/meto/agent/syntax_expander.py)** - Shorthand syntax expansion (@agent, ~skill)
- **[agent/todo.py](src/meto/agent/todo.py)** - Todo manager for multi-step task tracking
- **[agent/command.py](src/meto/agent/command.py)** - Slash command handlers (/exit, /help, /history, etc.)

### Agent Loop Flow

1. User prompt → syntax expansion (if applicable)
2. LLM call with system prompt + history + available tools
3. If tool calls: execute tools, append results to history, loop back to step 2
4. If no tool calls: return final response

### Syntax Shorthands

- **`@agent task`** - Expands to `run_task` tool call for the named agent
- **`~skill task`** - Expands to `load_skill` tool call for the named skill

### Tools Available

- `shell` - Execute bash/PowerShell commands
- `list_dir` - List directory contents
- `read_file` - Read file contents
- `write_file` - Create/overwrite files
- `edit_file` - Apply targeted edits (string replacement)
- `grep_search` - Search code with regex
- `fetch` - Fetch and parse web content
- `run_task` - Spawn subagent for isolated subtasks
- `load_skill` - Lazy-load domain expertise from `.meto/skills/`
- `manage_todos` - Task tracking
- `ask_user_question` - Ask user for clarification

### Extensibility

**Custom Agents** (`.meto/agents/{name}.md`): Define specialized agents with specific tool permissions and system prompts using YAML frontmatter:

```yaml
---
name: explore
description: Read-only exploration
tools:
  - shell
  - read_file
  - grep_search
---

Agent-specific prompt instructions...
```

**Skills** (`.meto/skills/{skill-name}/SKILL.md`): Domain expertise modules lazy-loaded via `load_skill` tool. Use for coding standards, domain knowledge, workflows, etc.

**Features** (`AGENT_FEATURES` in config): Toggle-able features:
- `agentsmd` - Include AGENTS.md in system prompt
- `subagents` - Enable `run_task` tool
- `skills` - Enable `load_skill` tool
- `todo_manager` - Enable `manage_todos` tool

## Configuration

Environment variables via `.env` (prefix: `METO_`):

```bash
# LLM configuration
METO_LLM_API_KEY=your_key
METO_LLM_BASE_URL=http://localhost:4444  # LiteLLM proxy
METO_DEFAULT_MODEL=gpt-4.1

# Loop tuning
METO_MAIN_AGENT_MAX_TURNS=100
METO_SUBAGENT_MAX_TURNS=25
METO_TOOL_TIMEOUT_SECONDS=300
METO_MAX_TOOL_OUTPUT_CHARS=50000

# Directories
METO_SESSION_DIR=~/.minimeto/sessions
METO_AGENTS_DIR=.meto/agents
METO_SKILLS_DIR=.meto/skills

# Features (comma-separated)
METO_AGENT_FEATURES=agentsmd,todo_manager,subagents,skills
```

## Linting

Ruff (format + lint) + basedpyright (type checking) + codespell. Tests excluded from type checking. Run via `just lint` or `uv run python devtools/lint.py`.
