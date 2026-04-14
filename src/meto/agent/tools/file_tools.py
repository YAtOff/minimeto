"""File and directory operations."""

import difflib
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from meto.agent.context import Context
from meto.agent.image_utils import encode_image, is_image
from meto.agent.shell import format_size, pick_shell_runner, run_shell, truncate
from meto.conf import settings

try:
    from tree_sitter_languages import get_language, get_parser

    _ts_available = True
except ImportError:
    _ts_available = False
    get_language = None  # type: ignore
    get_parser = None  # type: ignore

TS_AVAILABLE: bool = _ts_available

logger = logging.getLogger(__name__)

# --- Code Map Constants ---

# These queries target definitions across different languages.
QUERIES = {
    "python": """
        (class_definition name: (identifier) @name) @class
        (function_definition name: (identifier) @name) @func
    """,
    "javascript": """
        (class_declaration name: (identifier) @name) @class
        (function_declaration name: (identifier) @name) @func
        (method_definition name: (property_identifier) @name) @method
        (variable_declarator name: (identifier) @name value: [(arrow_function) (function_expression)]) @func
    """,
    "typescript": """
        (class_declaration name: (identifier) @name) @class
        (function_declaration name: (identifier) @name) @func
        (method_definition name: (property_identifier) @name) @method
        (interface_declaration name: (type_identifier) @name) @interface
    """,
}

# --- Error IDs ---
FILE_PATH_RESOLUTION_ERROR = "file_path_resolution_error"
FILE_READ_ERROR = "file_read_error"
FILE_WRITE_PERMISSION_DENIED = "file_write_permission_denied"
FILE_WRITE_IS_DIRECTORY = "file_write_is_directory"
FILE_WRITE_OS_ERROR = "file_write_os_error"
FILE_BINARY_READ_ERROR = "file_binary_read_error"
FILE_STAT_ERROR = "file_stat_error"

MAX_READ_LINES = 500


# --- Code Map logic ---


def detect_lang(path: str) -> str | None:
    """Detect language key for tree-sitter mapping based on file extension."""
    ext = Path(path).suffix.lower()
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
    }
    return mapping.get(ext)


def get_code_map(file_path: Path, lang_key: str) -> str:
    """Generates a structural map of a file to prevent LLM context flooding."""
    if not TS_AVAILABLE or lang_key not in QUERIES:
        return f"Structural mapping for {lang_key} is not supported."

    assert get_language is not None
    assert get_parser is not None

    try:
        language = get_language(lang_key)
        parser = get_parser(lang_key)

        code = file_path.read_bytes()
        tree = parser.parse(code)
        query = language.query(QUERIES[lang_key])
        captures = query.captures(tree.root_node)

        lines = []
        for node, tag in captures:
            # We only want the container node (the class/func), not the name identifier node
            if tag in ["class", "func", "method", "interface"]:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    continue

                name = code[name_node.start_byte : name_node.end_byte].decode("utf-8")
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1

                lines.append(f"[{tag.upper()}] {name} (Lines {start}-{end})")

        return "\n".join(lines) if lines else "No significant definitions found."
    except Exception as ex:
        logger.warning(f"Error generating code map for {file_path}: {ex}")
        return f"Error generating structural map: {ex}"


# --- Diff helpers ---


def is_binary_content(content: bytes) -> bool:
    """Check if content appears to be binary (non-text).

    The algorithm uses two heuristics:
    1. Null byte detection: If a null byte (\\x00) is found in the first 8KB.
    2. Non-printable ratio: If more than 30% of characters in the first 8KB are non-text.

    Args:
        content: Raw bytes to check

    Returns:
        True if content appears to be binary, False if text-like
    """
    try:
        # Check for null bytes (common in binary files)
        if b"\x00" in content[:8192]:
            return True

        # Check for high ratio of non-printable characters
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        sample = content[:8192]
        if not sample:
            return False

        non_text = sum(1 for byte in sample if byte not in text_chars)

        return non_text / len(sample) > 0.30
    except (TypeError, AttributeError, MemoryError) as ex:
        logger.warning(f"Error detecting binary content, treating as binary: {ex}")
        return True  # Fail safely


def generate_unified_diff(
    old_content: str | None,
    new_content: str,
    filepath: Path,
    max_lines: int | None = None,
    context_lines: int | None = None,
) -> str:
    """Generate a unified diff between old and new content.

    Args:
        old_content: Original content (None for new files)
        new_content: New content to write
        filepath: Path to the file
        max_lines: Maximum diff lines to show. Defaults to settings.DIFF_MAX_LINES if None.
        context_lines: Context lines around changes. Defaults to settings.DIFF_CONTEXT_LINES if None.

    Returns:
        Formatted unified diff string
    """
    if max_lines is None:
        max_lines = settings.DIFF_MAX_LINES
    if context_lines is None:
        context_lines = settings.DIFF_CONTEXT_LINES

    filename = filepath.name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Handle new file case
    # We manually construct the diff for new files to ensure a clean "+line" format
    # instead of the more complex diff format for an empty source.
    if old_content is None:
        lines = new_content.splitlines(keepends=True)
        header = f"--- /dev/null\t{timestamp}\n"
        header += f"+++ b/{filename}\t{timestamp}\n"
        diff_lines = [f"+{line}" for line in lines[:max_lines]]
        if len(lines) > max_lines:
            diff_lines.append(f"... ({len(lines) - max_lines} more lines)\n")
        return header + "".join(diff_lines)

    # Generate unified diff for existing file
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{filename}",
        tofile=f"b/{filename}",
        lineterm="",
        n=context_lines,
    )

    diff_text = "".join(diff)

    # Truncate if too large
    diff_lines_list = diff_text.splitlines(keepends=True)
    if len(diff_lines_list) > max_lines:
        diff_text = "".join(diff_lines_list[:max_lines])
        diff_text += f"\n... diff truncated ({len(diff_lines_list) - max_lines} more lines)\n"

    return diff_text


# --- File operations ---


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
                except OSError as e:
                    logger.debug(f"Could not get size for {entry}: {e}")

            size_str = format_size(size) if entry.is_file() else ""
            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                mtime_str = mtime.strftime("%Y-%m-%d %H:%M")
            except OSError as e:
                logger.debug(f"Could not get mtime for {entry}: {e}")
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
    """Read file contents with proper error handling, line numbering, and pagination.

    Args:
        _context: Execution context (unused)
        path: Path to the file to read
        start_line: 1-based line number to start reading from (inclusive, defaults to 1)
        end_line: 1-based line number to end reading at (inclusive, defaults to start_line + 499)

    Returns:
        The file content with line numbers or an error message string
    """

    try:
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            return f"Error: File does not exist: {path}"
        if not file_path.is_file():
            return f"Error: Not a file: {path}"

        # Image support: Detect if the file is an image
        if is_image(str(file_path)):
            try:
                mime_type, encoded_data = encode_image(str(file_path))
                return f"__METO_IMAGE__:data:{mime_type};base64,{encoded_data}"
            except (PermissionError, OSError) as e:
                return f"Error reading image file {path}: {e}"

        lines = file_path.read_text(encoding="utf-8").splitlines()
        total_lines = len(lines)
        file_size = file_path.stat().st_size

        # Enforce defaults and pagination
        effective_start = start_line if start_line is not None else 1
        effective_end = end_line if end_line is not None else effective_start + MAX_READ_LINES - 1

        # Code Map Interceptor: If file is large and range is wide, return map
        requested_range = effective_end - effective_start + 1
        if total_lines > 600 or file_size > 30000:
            # If no bounds were provided OR the requested range is very large (> 400 lines)
            if (start_line is None and end_line is None) or requested_range > 400:
                lang_key = detect_lang(str(file_path))
                if lang_key:
                    code_map = get_code_map(file_path, lang_key)
                    return (
                        f"FILE TOO LARGE ({total_lines} lines, {format_size(file_size)}). "
                        "To save context, I have generated a structural map:\n\n"
                        f"{code_map}\n\n"
                        "INSTRUCTION: Use read_file(path, start_line, end_line) to read a specific range."
                    )

        # Ensure range is valid and fits within limits
        if effective_end - effective_start >= MAX_READ_LINES:
            effective_end = effective_start + MAX_READ_LINES - 1

        # 0-indexed internal logic
        start_idx = max(0, min(effective_start - 1, total_lines))
        end_idx = max(0, min(effective_end, total_lines))

        if start_idx >= end_idx and total_lines > 0:
            return f"Error: Invalid range {effective_start}-{effective_end} for file with {total_lines} lines"

        selected_lines = lines[start_idx:end_idx]

        # Format with line numbers: "10 | content"
        formatted_lines = [f"{start_idx + i + 1} | {line}" for i, line in enumerate(selected_lines)]
        content = "\n".join(formatted_lines)

        # Build output with metadata and warnings
        is_truncated = start_idx > 0 or end_idx < total_lines
        header = f"[FILE: {path} | Lines {start_idx + 1}-{end_idx} of {total_lines}"
        if is_truncated:
            header += " | TRUNCATED"
        header += "]\n"

        result = header + content

        if is_truncated:
            footer = f"\n\n[TRUNCATION WARNING]: This file is {total_lines} lines long. You are seeing a {len(selected_lines)}-line window."
            if end_idx < total_lines:
                footer += f'\nTo see more, use: read_file(path="{path}", start_line={end_idx + 1})'
            footer += "\nTo find specific code, use the grep_search tool."
            result += footer

        return truncate(result, settings.MAX_TOOL_OUTPUT_CHARS)
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
    except UnicodeDecodeError:
        return f"Error: Cannot decode file {path} as UTF-8 text"
    except PermissionError:
        return f"Error: Permission denied accessing {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory, not a file: {path}"
    except OSError as ex:
        return f"Error modifying file {path}: {ex}"


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
    except UnicodeDecodeError:
        return f"Error: Cannot decode file {path} as UTF-8 text"
    except PermissionError:
        return f"Error: Permission denied accessing {path}"
    except IsADirectoryError:
        return f"Error: Path is a directory, not a file: {path}"
    except OSError as ex:
        return f"Error modifying file {path}: {ex}"


def write_file(_context: Context, path: str, content: str) -> str:
    """Write content to a file with proper error handling and diff output.

    Note:
        If the file exists, it will be read first to generate a diff.
        This requires read permissions even for write operations.
        Binary files are detected and handled without diff output.
        In multi-process scenarios, the file could change between read and write (race condition).
        For the AI agent use case (single-user), this is acceptable.

    Args:
        _context: Execution context (unused)
        path: Path to the file to write
        content: Complete content to write to the file

    Returns:
        Success message with diff or an error message string. Return formats:
        - New files: "Created {path} ({n} lines)\\n{diff}"
        - Modified files: "Updated {path} ({new} lines, was {old} lines)\\n{diff}"
        - Binary files: "Updated binary file: {path}\\nOld: {size} → New: {size}"
        - No changes: "No changes: {path} (content identical)"
        - Large files: "Updated large file: {path}\\n(Diff suppressed for large files)"
        - Errors: "Error [{ID}]: {description}"
    """
    try:
        file_path = Path(path).expanduser().resolve()
    except OSError as ex:
        logger.error(
            f"Failed to resolve path '{path}': {ex}",
            extra={"error_id": FILE_PATH_RESOLUTION_ERROR, "file_path": path},
            exc_info=True,
        )
        return f"Error [{FILE_PATH_RESOLUTION_ERROR}]: Error resolving path '{path}': {ex}"

    # Read existing content if file exists
    old_content: str | None = None
    file_existed = False
    was_binary = False

    try:
        if file_path.exists():
            file_existed = True
            try:
                # Check for binary file
                raw_bytes = file_path.read_bytes()
                if is_binary_content(raw_bytes):
                    was_binary = True
                else:
                    old_content = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, PermissionError) as e:
                # Handle unreadable files
                logger.error(
                    f"Failed to read existing file '{path}': {e}",
                    extra={
                        "error_id": FILE_READ_ERROR,
                        "file_path": path,
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                return f"Error [{FILE_READ_ERROR}]: Cannot read existing file: {e}"
            except IsADirectoryError as ex:
                logger.error(
                    f"Path is a directory '{path}': {ex}",
                    extra={"error_id": FILE_WRITE_IS_DIRECTORY, "file_path": path},
                    exc_info=True,
                )
                return f"Error [{FILE_WRITE_IS_DIRECTORY}]: Path is a directory, not a file: {path}"
            except OSError as ex:
                logger.error(
                    f"Failed to access existing file '{path}': {ex}",
                    extra={"error_id": FILE_READ_ERROR, "file_path": path},
                    exc_info=True,
                )
                return f"Error [{FILE_READ_ERROR}]: Error accessing file {path}: {ex}"
    except OSError as ex:
        logger.error(
            f"Failed to check existence of file '{path}': {ex}",
            extra={"error_id": FILE_READ_ERROR, "file_path": path},
            exc_info=True,
        )
        return f"Error [{FILE_READ_ERROR}]: Error accessing file {path}: {ex}"

    # Handle binary files
    if was_binary:
        try:
            try:
                old_size = file_path.stat().st_size
            except OSError as ex:
                logger.error(f"Failed to stat binary file '{path}': {ex}", exc_info=True)
                return f"Error [{FILE_STAT_ERROR}]: Cannot access file {path} for size info: {ex}"

            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            new_size = len(content.encode("utf-8"))
            return (
                f"Updated binary file: {path}\n"
                f"Old: {format_size(old_size)} → New: {format_size(new_size)}"
            )
        except PermissionError as ex:
            logger.error(
                f"Permission denied writing to binary file '{path}': {ex}",
                extra={"error_id": FILE_WRITE_PERMISSION_DENIED, "file_path": path},
                exc_info=True,
            )
            return f"Error [{FILE_WRITE_PERMISSION_DENIED}]: Permission denied writing to {path}"
        except OSError as ex:
            logger.error(
                f"OS error writing to binary file '{path}': {ex}",
                extra={"error_id": FILE_WRITE_OS_ERROR, "file_path": path},
                exc_info=True,
            )
            return f"Error [{FILE_WRITE_OS_ERROR}]: Error writing file {path}: {ex}"

    # Check if content is identical (no-op)
    if old_content is not None and old_content == content:
        return f"No changes: {path} (content identical)"

    # Check for large file - skip diff if too large
    if old_content is not None and len(old_content) > settings.DIFF_MAX_FILE_SIZE:
        try:
            old_size = len(old_content)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            new_size = len(content)
            return (
                f"Updated large file: {path}\n"
                f"Old: {old_size} chars → New: {new_size} chars\n"
                f"(Diff suppressed for large files)"
            )
        except PermissionError as ex:
            logger.error(
                f"Permission denied writing to large file '{path}': {ex}",
                extra={"error_id": FILE_WRITE_PERMISSION_DENIED, "file_path": path},
                exc_info=True,
            )
            return f"Error [{FILE_WRITE_PERMISSION_DENIED}]: Permission denied writing to {path}"
        except OSError as ex:
            logger.error(
                f"OS error writing to large file '{path}': {ex}",
                extra={"error_id": FILE_WRITE_OS_ERROR, "file_path": path},
                exc_info=True,
            )
            return f"Error [{FILE_WRITE_OS_ERROR}]: Error writing file {path}: {ex}"

    # Generate diff if enabled
    diff = ""
    if settings.DIFF_ENABLED:
        try:
            diff = generate_unified_diff(old_content, content, file_path)
            diff = f"\n{diff}"
        except Exception as ex:
            logger.warning(f"Failed to generate diff for '{path}': {ex}", exc_info=True)
            diff = "\n(Diff generation failed)"

    # Write the file
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    except PermissionError as ex:
        logger.error(
            f"Permission denied writing to file '{path}': {ex}",
            extra={"error_id": FILE_WRITE_PERMISSION_DENIED, "file_path": path},
            exc_info=True,
        )
        return f"Error [{FILE_WRITE_PERMISSION_DENIED}]: Permission denied writing to {path}"
    except IsADirectoryError as ex:
        logger.error(
            f"Path is a directory '{path}': {ex}",
            extra={"error_id": FILE_WRITE_IS_DIRECTORY, "file_path": path},
            exc_info=True,
        )
        return f"Error [{FILE_WRITE_IS_DIRECTORY}]: Path is a directory, not a file: {path}"
    except OSError as ex:
        logger.error(
            f"OS error writing to file '{path}': {ex}",
            extra={"error_id": FILE_WRITE_OS_ERROR, "file_path": path},
            exc_info=True,
        )
        return f"Error [{FILE_WRITE_OS_ERROR}]: Error writing file {path}: {ex}"

    # Build result message
    if file_existed:
        action = "Updated"
        old_lines = len(old_content.splitlines()) if old_content else 0
        new_lines = len(content.splitlines())
        summary = f"{action} {path} ({new_lines} lines, was {old_lines} lines)"
    else:
        action = "Created"
        new_lines = len(content.splitlines())
        summary = f"{action} {path} ({new_lines} lines)"

    return summary + diff


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
