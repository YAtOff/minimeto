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


def read_file(
    _context: Context,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Read file contents with proper error handling and optional line range.

    Args:
        _context: Execution context (unused)
        path: Path to the file to read
        start_line: 1-based line number to start reading from (inclusive)
        end_line: 1-based line number to end reading at (inclusive)

    Returns:
        The file content or an error message string
    """

    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File does not exist: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        lines = file_path.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)

        if start_line is not None or end_line is not None:
            # 1-based indexing for users (inclusive start/end)
            start = (start_line - 1) if start_line is not None else 0
            end = end_line if end_line is not None else total_lines

            # Bounds checking
            start = max(0, min(start, total_lines))
            end = max(0, min(end, total_lines))

            if start >= end:
                return f"Error: Invalid range {start_line}-{end_line} for file with {total_lines} lines"

            selected_lines = lines[start:end]
            content = "\n".join(selected_lines)
            if end < total_lines:
                content += "\n..."

            header = f"Reading lines {start + 1}-{end} of {total_lines} from {path}:\n"
            return header + truncate(content, settings.MAX_TOOL_OUTPUT_CHARS)

        content = "\n".join(lines)
        return truncate(content, settings.MAX_TOOL_OUTPUT_CHARS)
    except UnicodeDecodeError:
        return f"Error: Cannot decode file {path} as UTF-8 text"
    except PermissionError:
        return f"Error: Permission denied reading {path}"
    except OSError as ex:
        return f"Error reading file {path}: {ex}"


def replace_text_in_file(_context: Context, path: str, old_str: str, new_str: str) -> str:
    """Replace exactly one occurrence of old_str with new_str in a file.

    Args:
        _context: Execution context (unused)
        path: Path to the file to modify
        old_str: The literal text to find and replace
        new_str: The text to replace old_str with

    Returns:
        Success message or an error message string
    """
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File does not exist: {path}"

        content = file_path.read_text(encoding="utf-8")
        occurrences = content.count(old_str)

        if occurrences == 0:
            return f"Error: Could not find '{old_str}' in {path}"
        if occurrences > 1:
            return (
                f"Error: Found {occurrences} occurrences of '{old_str}' in {path}. "
                "Please provide more context to make the replacement unique."
            )

        new_content = content.replace(old_str, new_str)
        file_path.write_text(new_content, encoding="utf-8")
        return f"Successfully replaced '{old_str}' with '{new_str}' in {path}"
    except Exception as ex:
        return f"Error replacing text in {path}: {ex}"


def insert_in_file(_context: Context, path: str, insert_line: int, new_str: str) -> str:
    """Insert text at a specific line in a file.

    Args:
        _context: Execution context (unused)
        path: Path to the file to modify
        insert_line: 1-based line number where the new text will be inserted
        new_str: The text to insert

    Returns:
        Success message or an error message string
    """
    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File does not exist: {path}"

        lines = file_path.read_text(encoding="utf-8").splitlines()

        # 1-based indexing
        idx = max(0, min(insert_line - 1, len(lines)))
        lines.insert(idx, new_str)

        file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return f"Successfully inserted text at line {insert_line} in {path}"
    except Exception as ex:
        return f"Error inserting text in {path}: {ex}"


def write_file(_context: Context, path: str, content: str) -> str:
    """Write content to a file with proper error handling.

    Args:
        _context: Execution context (unused)
        path: Path to the file to write
        content: Complete content to write to the file

    Returns:
        Success message or an error message string
    """

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
            return (
                f"(timeout after {settings.TOOL_TIMEOUT_SECONDS}s). "
                "You can increase this limit by setting the METO_TOOL_TIMEOUT_SECONDS environment variable."
            )
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
    start_line = parameters.get("start_line")
    end_line = parameters.get("end_line")
    return read_file(context, path, start_line, end_line)


def handle_replace_text_in_file(context: Context, parameters: dict[str, Any]) -> str:
    """Handle file text replacement."""
    path = parameters.get("path", "")
    old_str = parameters.get("old_str", "")
    new_str = parameters.get("new_str", "")
    return replace_text_in_file(context, path, old_str, new_str)


def handle_insert_in_file(context: Context, parameters: dict[str, Any]) -> str:
    """Handle text insertion in file."""
    path = parameters.get("path", "")
    insert_line = parameters.get("insert_line", 1)
    new_str = parameters.get("new_str", "")
    return insert_in_file(context, path, insert_line, new_str)


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
