# minimeto

A minimal coding agent CLI tool. AI agent runs tool-calling loop with multiple tools for command execution.

## Philosophy

**Multiple tools + ONE loop (tool-calling) = capable coding agent**

meto provides a streamlined interface for AI-assisted coding through a simple but powerful architecture: an LLM with access to various tools (shell execution, file operations, grep, web fetch, task management) running in a continuous tool-calling loop until the task is complete.

## Features

- **Interactive & One-Shot Modes**: Run interactively with a REPL or execute single commands
- **Tool-Calling Loop**: Autonomous agent that can execute commands, read/write files, search code, and more
- **Subagent Pattern**: Spawn isolated agents for subtasks with fresh context
- **Custom Agents**: Define specialized agents with specific tool permissions
- **Skills System**: Lazy-loaded domain expertise modules for on-demand knowledge injection

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip

### Install from source

```bash
# Clone the repository
git clone <repository-url>
cd meto

# Install dependencies and run tests
just

# Or install as local tool
uv tool install --editable .
```

## Quick Start

### 1. Configure LLM Access

minimeto uses LiteLLM proxy for model-agnostic LLM access. Set up your environment:

```bash
# Create .env file
cat > .env << EOF
MINIMETO_LLM_API_KEY=your-api-key
MINIMETO_LLM_BASE_URL=model-api-endpoint
MINIMETO_DEFAULT_MODEL=model-name
EOF
```

### 2. Run Interactive Mode

```bash
# Start interactive session
uv run meto
```

### 3. One-Shot Mode

```bash
# Execute single command
uv run meto --one-shot --prompt "fix the bug in src/main.py"

# or
echo "fix the bug in src/main.py" | uv run meto --one-shot
```

## Configuration

Environment variables (`.env` supported):

| Variable | Description | Default |
|----------|-------------|---------|
| `MINIMETO_LLM_API_KEY` | API key for LLM provider | - |
| `MINIMETO_LLM_BASE_URL` | LLM provider API endpoint URL | - |
| `MINIMETO_DEFAULT_MODEL` | Model identifier | - |
| `MINIMETO_MAIN_AGENT_MAX_TURNS` | Max iterations for main agent | `100` |
| `MINIMETO_SUBAGENT_MAX_TURNS` | Max iterations for subagents | `25` |
| `MINIMETO_TOOL_TIMEOUT_SECONDS` | Shell command timeout | `300` |
| `MINIMETO_MAX_TOOL_OUTPUT_CHARS` | Max tool output length | `50000` |
| `MINIMETO_AGENTS_DIR` | Custom agents directory | `.meto/agents` |
| `MINIMETO_SKILLS_DIR` | Skills directory | `.meto/skills` |

## Core Concepts

### Agent Loop

1. User prompt → conversation history
2. LLM call with system prompt + history + available tools
3. If tool calls: execute tools, append results to history, loop back to step 2
4. If no tool calls: return final response

### Tools Available

- **shell**: Execute bash/PowerShell commands
- **read_files**: Read file contents
- **write_file**: Create or overwrite files
- **edit_file**: Apply targeted edits to files
- **grep**: Search code with regex patterns
- **web_fetch**: Fetch and parse web content
- **run_task**: Spawn subagent for isolated subtasks
- **load_skill**: Load domain expertise modules on-demand
- **manage_todos***: Task tracking (create, update, list, get)

## Customization

### Custom Agents

Define specialized agents in `.meto/agents/{name}.md`:

```markdown
---
name: reviewer
description: Code review specialist
tools:
  - read_files
  - grep
  - web_fetch
---

You are an expert code reviewer. Focus on:
- Security vulnerabilities
- Performance issues
- Best practices
- Code maintainability
```

### Skills System

Create domain expertise modules in `.meto/skills/{skill-name}/SKILL.md`:

```markdown
---
name: commit-message
description: Generate conventional commit messages
---

# Commit Message Skill

You are an expert at writing clear, informative git commit messages...
```

Skills are lazy-loaded only when needed via the `load_skill` tool.

## Development

```bash
# Primary workflows (via just)
just              # install + lint + test
just install      # sync dependencies
just lint         # ruff format + check
just test         # pytest
just build        # build wheel
just clean        # remove build artifacts

# Direct commands
uv run pytest                    # run tests
uv run python devtools/lint.py   # lint
uv build                         # build
uv tool install --editable .     # install as local tool
```

## Architecture

- `src/meto/cli.py` - CLI interface and interactive mode
- `src/meto/agent/agent_loop.py` - Main agent loop
- `src/meto/agent/agent.py` - Agent class factory
- `src/meto/agent/tool_runner.py` - Tool execution implementations
- `src/meto/agent/tool_schema.py` - Tool schemas (OpenAI format)
- `src/meto/agent/loaders/` - Agent, skill, and frontmatter loaders

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions welcome! Please check existing issues or open a new one to discuss changes.
