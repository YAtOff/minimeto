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
uv run python scripts/lint.py    # lint
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
- **[agent/tool_runner.py](src/meto/agent/tool_runner.py)** - Lightweight tool dispatcher
- **[agent/tools/](src/meto/agent/tools/)** - Domain-specific tool implementations (file, net, task, skill, etc.)
- **[agent/orchestrator/](src/meto/agent/orchestrator/)** - LLM client management and signal handling
- **[agent/loaders/](src/meto/agent/loaders/)** - Unified resource loaders for agents, skills, and rules
- **[agent/tool_registry.py](src/meto/agent/tool_registry.py)** - Runtime tool discovery registry with keyword search
- **[agent/mcp_client.py](src/meto/agent/mcp_client.py)** - FastMCP client integration for external tool discovery
- **[agent/reasoning_log.py](src/meto/agent/reasoning_log.py)** - Structured logging (JSONL trace files + rich stderr)
- **[agent/shell.py](src/meto/agent/shell.py)** - Shell execution utilities (prefers zsh > bash > PowerShell)
- **[agent/tool_schema.py](src/meto/agent/tool_schema.py)** - OpenAI-compatible tool schemas
- **[agent/session.py](src/meto/agent/session.py)** - Conversation history and state management
- **[agent/context.py](src/meto/agent/context.py)** - Context object passed to tools (todos, history)
- **[agent/system_prompt.py](src/meto/agent/system_prompt.py)** - System prompt builder with feature flags
- **[agent/syntax_expander.py](src/meto/agent/syntax_expander.py)** - Shorthand syntax expansion (@agent, ~skill)
- **[agent/todo.py](src/meto/agent/todo.py)** - Todo manager for multi-step task tracking
- **[agent/command.py](src/meto/agent/command.py)** - Slash command handlers (/exit, /help, /history, etc.)
- **[agent/permissions.py](src/meto/agent/permissions.py)** - Session-scoped permission manager for sensitive operations
- **[agent/hooks/](src/meto/agent/hooks/)** - Pre/post-tool hooks for security and permissions

### Agent Loop Flow

1. User prompt → syntax expansion (if applicable)
2. Initialize MCP tools from `.meto/mcp.json` (if configured)
3. LLM call with system prompt + history + available tools
4. If tool calls: **run pre-tool hooks** (permissions, security) → execute tools → append results to history → loop back to step 3
5. If no tool calls: return final response

### Permission System

**Hooks** provide a clean way to intercept tool calls before execution:
- **`SafeReadHook`**: Blocks reading sensitive files (e.g., `.env`)
- **`FilePermissionHook`**: Asks permission before accessing files outside CWD
- **`ShellPermissionHook`**: Asks permission before executing shell commands
- **`FetchPermissionHook`**: Asks permission before fetching web resources

**Permission Prompts**: When a hook requires permission, the user sees:
```
[Permission Required] Execute shell command: ls -la
(yes/no/always):
```

- **yes**: Allow this one operation
- **no**: Deny this operation
- **always**: Allow all similar operations this session (cached in memory)

**Global Bypass**: Set `METO_PERMISSIONS_ENABLED=false` to disable all permission checks.

### Syntax Shorthands

- **`@agent task`** - Expands to `run_task` tool call for the named agent
- **`~skill task`** - Expands to `load_skill` tool call for the named skill

### Tools Available

- `shell` - Execute bash/PowerShell commands
- `list_dir` - List directory contents
- `read_file` - Read file contents (supports optional `start_line` and `end_line` for range reading)
- `write_file` - Create/overwrite files
- `replace_text_in_file` - Replace exactly one occurrence of a string (surgical edits)
- `insert_in_file` - Insert text at a specific line number
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
- `registry_tools` - Include MCP/registry tools in wildcard tool access

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

# Security
METO_PERMISSIONS_ENABLED=true  # Enable permission checks for sensitive operations
```

## Linting

Ruff (format + lint) + basedpyright (type checking) + codespell. Tests excluded from type checking. Run via `just lint` or `uv run python scripts/lint.py`.

## MCP Integration

**FastMCP Client** ([mcp_client.py](src/meto/agent/mcp_client.py)) enables runtime tool discovery from external MCP servers:

Configure via `.meto/mcp.json`:
```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-chrome-devtools"],
      "env": {"PATH": "$PATH"}
    }
  }
}
```

Tools are automatically discovered and registered in the runtime [ToolRegistry](src/meto/agent/tool_registry.py), supporting keyword search for dynamic tool resolution.

**Logging**: Agent activity is logged to:
- JSONL trace files: `{LOG_DIR}/agent_reasoning_{timestamp}_{random}.jsonl`
- Rich-colored stderr output (human-readable)

## Built-in Agents

Default agents are located in `src/meto/resources/agents/`.

- **screenshotter** - Web page screenshots via Chrome DevTools MCP
- **explore** - Read-only codebase exploration
- **code** - Code writing and editing
- **plan** - Implementation planning

## Available Skills

Default skills are located in `src/meto/resources/skills/`.

- **prd** - PRD generator
- **context7-docs** - Context7 documentation
- **python-styleguide** - Python coding standards
- **git-commit** - Git commit conventions
- **git-worktrees** - Git worktree management
