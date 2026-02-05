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
                "Use this for reading configuration files, source code, or any text file."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    }
                },
                "required": ["path"],
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
]

TOOLS_BY_NAME = {tool["function"]["name"]: tool for tool in TOOLS}
AVAILABLE_TOOLS = list(TOOLS_BY_NAME.keys())
