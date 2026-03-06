"""File and directory operations."""

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from meto.agent.context import Context
from meto.agent.shell import format_size, pick_shell_runner, run_shell, truncate
from meto.conf import settings


def list_directory(
    _context: Context, path: str = ".", recursive: bool = False, include_hidden: bool = False
) -> str:
    """List directory contents with structured output."""

    try:
        dir_path = Path(path).expanduser().resolve()
        if not dir_path.exists():
            return f"Error: Path does not exist: {path}"
        if not dir_path.is_dir():
            return f"Error: Not a directory: {path}"
    except OSError as ex:
        return f"Error accessing path '{path}': {ex}"

    lines: list[str] = []
    lines.append(f"{dir_path}:")

    try:
        if recursive:
            entries = sorted(dir_path.rglob("*"), key=lambda p: (p.parent, p.name))
        else:
            entries = sorted(dir_path.iterdir(), key=lambda p: p.name)

        for entry in entries:
            if not include_hidden and entry.name.startswith("."):
                continue

            entry_type = "dir" if entry.is_dir() else "file"
            size = 0
            if entry.is_file():
                try:
                    size = entry.stat().st_size
                except OSError:
                    pass

            size_str = format_size(size) if entry.is_file() else ""
            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            except OSError:
                mtime_str = "?"

            name = entry.name
            if recursive:
                rel_path = entry.relative_to(dir_path)
                name = str(rel_path)
                if entry.is_dir():
                    name = str(rel_path) + "/"

            size_col = f"    {size_str:>8}" if size_str else "           "
            lines.append(f"  {name:<30} ({entry_type:<4}){size_col}    {mtime_str}")

    except PermissionError:
        return f"Error: Permission denied accessing: {path}"
    except OSError as ex:
        return f"Error listing directory: {ex}"

    if len(lines) == 1:
        lines.append("  (empty directory)")

    return "\n".join(lines)


def read_file(_context: Context, path: str) -> str:
    """Read file contents with proper error handling."""

    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File does not exist: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        content = file_path.read_text(encoding="utf-8")
        return truncate(content, settings.MAX_TOOL_OUTPUT_CHARS)
    except UnicodeDecodeError:
        return f"Error: Cannot decode file {path} as UTF-8 text"
    except PermissionError:
        return f"Error: Permission denied reading {path}"
    except OSError as ex:
        return f"Error reading file {path}: {ex}"


def write_file(_context: Context, path: str, content: str) -> str:
    """Write content to a file with proper error handling."""

    try:
        file_path = Path(path).expanduser().resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {len(content)} chars to {path}"
    except PermissionError:
        return f"Error: Permission denied writing to {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory, not a file: {path}"
    except OSError as ex:
        return f"Error writing file {path}: {ex}"


def run_grep_search(
    _context: Context, pattern: str, path: str = ".", case_insensitive: bool = False
) -> str:
    """Search for pattern in files using ripgrep (rg) with fallback to grep/Select-String."""

    if not pattern.strip():
        return "Error: Empty search pattern"

    try:
        search_path = Path(path).expanduser().resolve()
        if not search_path.exists():
            return f"Error: Path does not exist: {path}"
    except OSError as ex:
        return f"Error accessing path '{path}': {ex}"

    rg = shutil.which("rg")
    if rg:
        args: list[str] = [
            rg,
            "--line-number",
            "--no-heading",
        ]
        if case_insensitive:
            args.append("-i")

        # `--` ensures patterns beginning with '-' are not interpreted as options.
        args += ["--", pattern, str(search_path)]

        try:
            completed = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=settings.TOOL_TIMEOUT_SECONDS,
                cwd=os.getcwd(),
            )
        except subprocess.TimeoutExpired:
            return f"(timeout after {settings.TOOL_TIMEOUT_SECONDS}s)"
        except OSError as ex:
            return f"(search execution error: {ex})"

        output = (completed.stdout or "") + (completed.stderr or "")
        output = output.strip() or "(empty)"
        return truncate(output, settings.MAX_TOOL_OUTPUT_CHARS)
    else:
        runner = pick_shell_runner()
        if runner and ("bash" in runner[0] or "sh" in runner[0]):
            flag = "-i" if case_insensitive else ""
            cmd = f'grep -R {flag} -n "{pattern}" "{path}" 2>/dev/null || true'
        elif runner and ("powershell" in runner[0] or "pwsh" in runner[0]):
            flag = "" if case_insensitive else "-CaseSensitive"
            cmd = (
                f'Select-String -Path "{path}\\*" -Pattern "{pattern}" {flag} '
                "| Select-Object -First 100"
            )
        else:
            return "Error: No suitable search tool found (need rg, grep, or PowerShell)"

    return run_shell(cmd)


def handle_shell(_context: Context, parameters: dict[str, Any]) -> str:
    """Handle shell command execution."""
    command = parameters.get("command", "")
    return run_shell(command)


def handle_list_dir(context: Context, parameters: dict[str, Any]) -> str:
    """Handle directory listing."""
    path = parameters.get("path", ".")
    recursive = parameters.get("recursive", False)
    include_hidden = parameters.get("include_hidden", False)
    return list_directory(context, path, recursive, include_hidden)


def handle_read_file(context: Context, parameters: dict[str, Any]) -> str:
    """Handle file reading."""
    path = parameters.get("path", "")
    return read_file(context, path)


def handle_write_file(context: Context, parameters: dict[str, Any]) -> str:
    """Handle file writing."""
    path = parameters.get("path", "")
    content = parameters.get("content", "")
    return write_file(context, path, content)


def handle_grep_search(context: Context, parameters: dict[str, Any]) -> str:
    """Handle pattern search."""
    pattern = parameters.get("pattern", "")
    path = parameters.get("path", ".")
    case_insensitive = parameters.get("case_insensitive", False)
    return run_grep_search(context, pattern, path, case_insensitive)
