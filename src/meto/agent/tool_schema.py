"""Model-facing tool schemas.

This module defines the JSON schemas exposed to the LLM via the OpenAI tools API.

Architectural constraint:
    Keep this module import-light. Tool *execution* lives in
    :mod:`meto.agent.tool_runner`.
"""

from __future__ import annotations

from typing import Any

from meto.agent.shell import get_shell_name

# Model-facing tool schemas (OpenAI function calling / tools API).
#
# Important architectural rule:
# - This module must stay import-light and must not import tool runtime code.
# - Tool execution lives in `meto.agent.tool_runner`.

SHELL_NAME = get_shell_name()

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                f"Execute shell commands using {SHELL_NAME}. "
                "Use ONLY when other tools cannot do the job. "
                "Use read_file/write_file/fetch/grep_search with GREATER PRIORITY."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute.",
                    }
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": (
                "List directory contents with structured output showing names, types, sizes, and timestamps. "
                "Use this for browsing the filesystem structure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (defaults to current working directory if empty).",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Whether to list subdirectories recursively.",
                        "default": False,
                    },
                    "include_hidden": {
                        "type": "boolean",
                        "description": "Whether to include hidden files and directories (those starting with a dot).",
                        "default": False,
                    },
                },
                "required": [],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file and return them as text. "
                "Optionally specify a line range."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The 1-based line number to start reading from (inclusive).",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "The 1-based line number to end reading at (exclusive).",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "replace_text_in_file",
            "description": (
                "Replace exactly one occurrence of a string with another string in a file. "
                "Always provide enough context in old_str to ensure it matches exactly once."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to modify.",
                    },
                    "old_str": {
                        "type": "string",
                        "description": "The exact string to replace.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "The replacement string.",
                    },
                },
                "required": ["path", "old_str", "new_str"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insert_in_file",
            "description": "Insert text at a specific 1-based line number in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to modify.",
                    },
                    "insert_line": {
                        "type": "integer",
                        "description": "The 1-based line number where the text should be inserted.",
                    },
                    "new_str": {
                        "type": "string",
                        "description": "The text to insert.",
                    },
                },
                "required": ["path", "insert_line", "new_str"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file. Creates parent directories if needed. "
                "Use this for creating or modifying files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file.",
                    },
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep_search",
            "description": (
                "Search for a text pattern in files within a directory. "
                "Uses ripgrep (rg) if available, otherwise grep or Select-String. "
                "Returns matching lines with file paths and line numbers."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for (supports regex).",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path to search in (defaults to current directory).",
                    },
                    "case_insensitive": {
                        "type": "boolean",
                        "description": "Whether to ignore case when matching.",
                        "default": False,
                    },
                },
                "required": ["pattern"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch",
            "description": (
                "Fetch web resources via HTTP GET. Returns response body as text. "
                "Handles redirects automatically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "max_bytes": {
                        "type": "integer",
                        "description": "Max response bytes (default: 100000)",
                    },
                },
                "required": ["url"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user_question",
            "description": "Ask the user a question and return their response",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The question to ask the user",
                    }
                },
                "required": ["question"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "manage_todos",
            "description": (
                "Update the todo list. Use to plan and track progress on multi-step todos. "
                "Mark todos in_progress before starting, completed when done. "
                "Only ONE todo can be in_progress at a time."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "Complete list of todos (replaces existing)",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Todo description",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Todo status",
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": "Present tense action, e.g. 'Reading files'",
                                },
                            },
                            "required": ["content", "status", "activeForm"],
                        },
                    }
                },
                "required": ["items"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_available_tools",
            "description": (
                "Searches the tool library for useful tools. "
                "Use this when you don't have a tool for a specific task. "
                "Returns a list of 'ToolName: Description'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Keywords or natural language description of the task "
                            "(e.g., 'git operations', 'deployment')."
                        ),
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Max number of tools to return (default: 3).",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_task",
            "description": (
                "Spawn subagent for isolated subtask. Each agent type has specific tools."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Short task name (3-5 words)",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Detailed instructions for subagent",
                    },
                    "agent_name": {
                        "type": "string",
                        "description": "Name of agent to spawn",
                    },
                },
                "required": ["description", "prompt", "agent_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_skill",
            "description": (
                "Load domain expertise for specialized tasks. "
                "Use when you need domain-specific knowledge not in your base knowledge. "
                "Available skills are listed in the system prompt."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of skill to load (e.g., 'code-review', 'commit-message')",
                    }
                },
                "required": ["skill_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_agent",
            "description": (
                "Load a skill-local agent configuration. "
                "Agents defined in a skill's agents/ subfolder are domain-specific subagents. "
                "This loads the agent configuration - use run_task to execute it. "
                "Only works when a skill has been loaded via load_skill.\n\n"
                "Example workflow:\n"
                "1. load_skill('python') - Load the python skill\n"
                "2. load_agent('reviewer') - Load the reviewer agent from the python skill\n"
                "3. run_task('reviewer', 'review this code') - Execute the reviewer agent\n\n"
                "Skill-local agents have specialized tool permissions and prompts for their domain."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_name": {
                        "type": "string",
                        "description": "Name of the skill-local agent to load (filename without .md extension)",
                    },
                },
                "required": ["agent_name"],
                "additionalProperties": False,
            },
        },
    },
]

TOOLS_BY_NAME = {tool["function"]["name"]: tool for tool in TOOLS}
AVAILABLE_TOOLS = list(TOOLS_BY_NAME.keys())
