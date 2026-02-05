# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
uv run meto                      # run the agent
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

### Agent Loop Flow

1. User prompt → conversation history
2. LLM call with system prompt + history + available tools
3. If tool calls: execute tools, append results to history, loop back to step 2
4. If no tool calls: return final response

### Tools Available

- `shell` - Execute bash/PowerShell commands
- `read_files` - Read file contents
- `write_file` - Create/overwrite files
- `edit_file` - Apply targeted edits (string replacement)
- `grep` - Search code with regex
- `web_fetch` - Fetch and parse web content
- `run_task` - Spawn subagent for isolated subtasks
- `load_skill` - Lazy-load domain expertise from `.meto/skills/`
- `manage_todos` - Task tracking

### Extensibility

**Custom Agents** (`.meto/agents/{name}.md`): Define specialized agents with specific tool permissions and system prompts using YAML frontmatter.

**Skills** (`.meto/skills/{skill-name}/SKILL.md`): Domain expertise modules lazy-loaded via `load_skill` tool.

## Configuration

Environment variables via `.env` (prefix: `MINIMETO_`):

- `LLM_API_KEY`, `LLM_BASE_URL`, `DEFAULT_MODEL` - LiteLLM proxy configuration
- `MAIN_AGENT_MAX_TURNS`, `SUBAGENT_MAX_TURNS` - Loop limits
- `TOOL_TIMEOUT_SECONDS`, `MAX_TOOL_OUTPUT_CHARS` - Execution constraints
- `AGENTS_DIR`, `SKILLS_DIR` - Customization paths

## Linting

Ruff (format + lint) + basedpyright (type checking) + codespell. Tests excluded from type checking. Run via `just lint` or `uv run python devtools/lint.py`.
