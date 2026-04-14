from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from meto.agent.context import Context
from meto.agent.tools.file_tools import (
    handle_grep_search,
    handle_insert_in_file,
    handle_list_dir,
    handle_read_file,
    handle_replace_text_in_file,
    handle_write_file,
    insert_in_file,
    list_directory,
    read_file,
    replace_text_in_file,
    run_grep_search,
    write_file,
)


@pytest.fixture
def mock_context():
    return MagicMock(spec=Context)


def test_list_directory_exists(tmp_path, mock_context):
    # Create some files and dirs
    (tmp_path / "file1.txt").write_text("hello")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file2.txt").write_text("world")

    result = list_directory(mock_context, str(tmp_path))
    assert str(tmp_path) in result
    assert "file1.txt" in result
    assert "subdir" in result


def test_list_directory_not_found(mock_context):
    result = list_directory(mock_context, "/non/existent/path")
    assert "Error: Path does not exist" in result


def test_read_file_success(tmp_path, mock_context):
    file_path = tmp_path / "test.txt"
    content = "test content"
    file_path.write_text(content)

    result = read_file(mock_context, str(file_path))
    assert "1 | test content" in result
    assert "[FILE: " in result


def test_read_file_range(tmp_path, mock_context):
    file_path = tmp_path / "range.txt"
    content = "line1\nline2\nline3\nline4\nline5"
    file_path.write_text(content)

    result = read_file(mock_context, str(file_path), start_line=2, end_line=4)
    assert "Lines 2-4" in result
    assert "2 | line2\n3 | line3\n4 | line4" in result
    assert "1 | line1" not in result
    assert "5 | line5" not in result


def test_read_file_pagination(tmp_path, mock_context):
    from meto.agent.tools.file_tools import MAX_READ_LINES

    file_path = tmp_path / "large.txt"
    content = "\n".join([f"line{i + 1}" for i in range(MAX_READ_LINES + 10)])
    file_path.write_text(content)

    # Read without range - should truncate to MAX_READ_LINES
    result = read_file(mock_context, str(file_path))
    assert f"Lines 1-{MAX_READ_LINES}" in result
    assert "TRUNCATED" in result
    assert "TRUNCATION WARNING" in result
    assert f'read_file(path="{file_path}", start_line={MAX_READ_LINES + 1})' in result
    assert f"{MAX_READ_LINES} | line{MAX_READ_LINES}" in result
    assert f"{MAX_READ_LINES + 1} | line{MAX_READ_LINES + 1}" not in result


def test_read_file_not_found(mock_context):
    result = read_file(mock_context, "/non/existent/file")
    assert "Error: File does not exist" in result


def test_write_file_success(tmp_path, mock_context):
    file_path = tmp_path / "new_file.txt"
    content = "new content"

    result = write_file(mock_context, str(file_path), content)
    assert "Created" in result
    assert file_path.read_text() == content


def test_replace_text_in_file_success(tmp_path, mock_context):
    file_path = tmp_path / "replace.txt"
    content = "hello world"
    file_path.write_text(content)

    result = replace_text_in_file(mock_context, str(file_path), "world", "meto")
    assert "Successfully replaced" in result
    assert file_path.read_text() == "hello meto"


def test_replace_text_in_file_duplicate(tmp_path, mock_context):
    file_path = tmp_path / "duplicate.txt"
    content = "hello world world"
    file_path.write_text(content)

    result = replace_text_in_file(mock_context, str(file_path), "world", "meto")
    assert "Error: Found 2 occurrences" in result


def test_insert_in_file_success(tmp_path, mock_context):
    file_path = tmp_path / "insert.txt"
    content = "line1\nline2"
    file_path.write_text(content)

    result = insert_in_file(mock_context, str(file_path), 2, "inserted")
    assert "Successfully inserted" in result
    assert file_path.read_text() == "line1\ninserted\nline2\n"


def test_run_grep_search_mock(mock_context):
    with patch("shutil.which", return_value="/usr/bin/rg"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "file.txt:1:match"
            mock_run.return_value.stderr = ""

            result = run_grep_search(mock_context, "match", path=".")
            assert "file.txt:1:match" in result
            mock_run.assert_called_once()


def test_run_grep_search_timeout(mock_context):
    import subprocess

    from meto.conf import settings

    with patch("shutil.which", return_value="/usr/bin/rg"):
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="rg", timeout=settings.TOOL_TIMEOUT_SECONDS),
        ):
            result = run_grep_search(mock_context, "match", path=".")
            assert f"(timeout after {settings.TOOL_TIMEOUT_SECONDS}s)" in result
            assert "METO_TOOL_TIMEOUT_SECONDS" in result


def test_handle_list_dir(mock_context):
    with patch("meto.agent.tools.file_tools.list_directory") as mock_list:
        mock_list.return_value = "list output"
        params = {"path": ".", "recursive": True}
        result = handle_list_dir(mock_context, params)
        assert result == "list output"
        mock_list.assert_called_once_with(mock_context, ".", True, False)


def test_handle_read_file(mock_context):
    with patch("meto.agent.tools.file_tools.read_file") as mock_read:
        mock_read.return_value = "file content"
        params = {"path": "test.txt", "start_line": 1, "end_line": 10}
        result = handle_read_file(mock_context, params)
        assert result == "file content"
        mock_read.assert_called_once_with(mock_context, "test.txt", 1, 10)


def test_handle_replace_text_in_file(mock_context):
    with patch("meto.agent.tools.file_tools.replace_text_in_file") as mock_replace:
        mock_replace.return_value = "success"
        params = {"path": "test.txt", "old_str": "old", "new_str": "new"}
        result = handle_replace_text_in_file(mock_context, params)
        assert result == "success"
        mock_replace.assert_called_once_with(mock_context, "test.txt", "old", "new")


def test_handle_insert_in_file(mock_context):
    with patch("meto.agent.tools.file_tools.insert_in_file") as mock_insert:
        mock_insert.return_value = "success"
        params = {"path": "test.txt", "insert_line": 5, "new_str": "content"}
        result = handle_insert_in_file(mock_context, params)
        assert result == "success"
        mock_insert.assert_called_once_with(mock_context, "test.txt", 5, "content")


def test_handle_write_file(mock_context):
    with patch("meto.agent.tools.file_tools.write_file") as mock_write:
        mock_write.return_value = "success"
        params = {"path": "test.txt", "content": "data"}
        result = handle_write_file(mock_context, params)
        assert result == "success"
        mock_write.assert_called_once_with(mock_context, "test.txt", "data")


def test_handle_grep_search(mock_context):
    with patch("meto.agent.tools.file_tools.run_grep_search") as mock_grep:
        mock_grep.return_value = "grep results"
        params = {"pattern": "findme", "path": "src"}
        result = handle_grep_search(mock_context, params)
        assert result == "grep results"
        mock_grep.assert_called_once_with(mock_context, "findme", "src", False)


def test_replace_text_in_file_unicode_error(tmp_path, mock_context):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    with patch.object(
        Path, "read_text", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
    ):
        result = replace_text_in_file(mock_context, str(test_file), "old", "new")
        assert "Error: Cannot decode file" in result


def test_replace_text_in_file_permission_error(tmp_path, mock_context):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
        result = replace_text_in_file(mock_context, str(test_file), "old", "new")
        assert "Error: Permission denied accessing" in result


def test_replace_text_in_file_is_a_directory_error(tmp_path, mock_context):
    test_file = tmp_path / "test_dir"
    test_file.mkdir()
    # Path.read_text on a directory raises IsADirectoryError (on some systems or if mocked)
    with patch.object(Path, "read_text", side_effect=IsADirectoryError("Is a directory")):
        result = replace_text_in_file(mock_context, str(test_file), "old", "new")
        assert "Error: Path is a directory" in result


def test_replace_text_in_file_unexpected_error_bubbles_up(tmp_path, mock_context):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    with patch.object(Path, "read_text", side_effect=NameError("bug")):
        with pytest.raises(NameError):
            replace_text_in_file(mock_context, str(test_file), "old", "new")


def test_insert_in_file_unexpected_error_bubbles_up(tmp_path, mock_context):
    test_file = tmp_path / "test.txt"
    test_file.write_text("dummy")
    with patch.object(Path, "read_text", side_effect=NameError("bug")):
        with pytest.raises(NameError):
            insert_in_file(mock_context, str(test_file), 1, "new")


# --- Diff functionality tests ---


class TestWriteFileDiff:
    """Tests for write_file diff output."""

    def test_create_new_file_shows_additions(self, tmp_path, mock_context):
        """Test that new file creation shows all lines as additions."""
        file_path = tmp_path / "new.txt"
        result = write_file(mock_context, str(file_path), "line1\nline2\n")

        assert "Created" in result
        assert "+line1" in result
        assert "+line2" in result
        assert "--- /dev/null" in result
        assert "+++ b/new.txt" in result
        assert file_path.exists()

    def test_modify_existing_file_shows_diff(self, tmp_path, mock_context):
        """Test that modifying a file shows unified diff."""
        file_path = tmp_path / "existing.txt"
        file_path.write_text("old line\nunchanged\n")

        result = write_file(mock_context, str(file_path), "new line\nunchanged\n")

        assert "Updated" in result
        assert "-old line" in result
        assert "+new line" in result
        assert "--- a/existing.txt" in result
        assert "+++ b/existing.txt" in result

    def test_identical_content_shows_no_changes(self, tmp_path, mock_context):
        """Test that writing identical content shows 'No changes' message."""
        file_path = tmp_path / "same.txt"
        file_path.write_text("same content\n")

        result = write_file(mock_context, str(file_path), "same content\n")

        assert "No changes" in result
        assert "identical" in result.lower()

    def test_empty_file_creation(self, tmp_path, mock_context):
        """Test that creating empty file works correctly."""
        file_path = tmp_path / "empty.txt"
        result = write_file(mock_context, str(file_path), "")

        assert "Created" in result
        assert file_path.exists()
        assert file_path.read_text() == ""

    def test_empty_to_content_shows_additions(self, tmp_path, mock_context):
        """Test that going from empty to content shows additions."""
        file_path = tmp_path / "was_empty.txt"
        file_path.write_text("")

        result = write_file(mock_context, str(file_path), "new content\n")

        assert "Updated" in result
        assert "+new content" in result


class TestBinaryDetection:
    """Tests for binary file detection."""

    def test_detects_null_bytes_as_binary(self, tmp_path, mock_context):
        """Test that files with null bytes are treated as binary."""
        from meto.agent.tools.file_tools import is_binary_content

        assert is_binary_content(b"\x00\x01\x02") is True

    def test_detects_text_as_non_binary(self, tmp_path, mock_context):
        """Test that text files are not treated as binary."""
        from meto.agent.tools.file_tools import is_binary_content

        assert is_binary_content(b"Hello, world!\n") is False

    def test_binary_file_shows_size_change(self, tmp_path, mock_context):
        """Test that binary files show size change instead of diff."""
        file_path = tmp_path / "binary.bin"
        file_path.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        result = write_file(mock_context, str(file_path), "text content")

        # Should show binary file handling
        assert "Updated binary file" in result
        assert "→" in result
        assert "---" not in result
        assert "+++" not in result


class TestDiffGeneration:
    """Tests for generate_unified_diff helper."""

    def test_new_file_diff_format(self, tmp_path):
        """Test diff format for new files."""
        from meto.agent.tools.file_tools import generate_unified_diff

        diff = generate_unified_diff(None, "line1\nline2\n", Path("test.txt"))

        assert "--- /dev/null" in diff
        assert "+++ b/test.txt" in diff
        assert "+line1" in diff
        assert "+line2" in diff

    def test_modified_file_diff_format(self, tmp_path):
        """Test diff format for modified files."""
        from meto.agent.tools.file_tools import generate_unified_diff

        old = "line1\nline2\nline3\n"
        new = "line1\nmodified\nline3\n"
        diff = generate_unified_diff(old, new, Path("test.txt"))

        assert "--- a/test.txt" in diff
        assert "+++ b/test.txt" in diff
        assert "-line2" in diff
        assert "+modified" in diff

    def test_diff_truncation(self, tmp_path):
        """Test that large diffs are truncated."""
        from meto.agent.tools.file_tools import generate_unified_diff

        # Create content with many lines
        large_content = "\n".join([f"line {i}" for i in range(200)])
        diff = generate_unified_diff(None, large_content, Path("test.txt"), max_lines=50)

        # Should indicate truncation
        assert "more lines" in diff.lower() or "truncated" in diff.lower()

    def test_generate_diff_custom_context_lines(self):
        """Test that custom context_lines parameter affects diff output."""
        from meto.agent.tools.file_tools import generate_unified_diff

        old = "1\n2\n3\n4\n5\n6\n"
        new = "1\n2\nCHANGED\n4\n5\n6\n"
        # With 1 context line, we should see 2 and 4 but not 1 or 5
        diff = generate_unified_diff(old, new, Path("test.txt"), context_lines=1)

        assert " 2" in diff
        assert " 4" in diff
        assert " 1" not in diff
        assert " 5" not in diff


class TestWriteFileErrors:
    """Tests for write_file error handling."""

    def test_large_file_diff_suppression(self, tmp_path, mock_context):
        """Test that files exceeding DIFF_MAX_FILE_SIZE show summary instead of diff."""
        from meto.conf import settings

        file_path = tmp_path / "large.txt"
        large_content = "x" * (settings.DIFF_MAX_FILE_SIZE + 1000)
        file_path.write_text(large_content)

        result = write_file(mock_context, str(file_path), "modified " + large_content)

        assert "Diff suppressed for large files" in result
        assert "Updated large file" in result
        assert "---" not in result
        assert "+++" not in result

    def test_write_file_unicode_decode_error_on_existing(self, tmp_path, mock_context):
        """Test that UnicodeDecodeError when reading existing file is handled."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"\xff\xfe")  # Invalid UTF-8

        result = write_file(mock_context, str(file_path), "new content")

        assert "Error [file_read_error]" in result
        assert "Cannot read existing file" in result
        assert file_path.read_bytes() == b"\xff\xfe"  # File shouldn't be modified

    def test_write_file_path_resolution_error(self, mock_context):
        """Test that OSError during path resolution is handled."""
        with patch.object(Path, "resolve", side_effect=OSError("Invalid path")):
            result = write_file(mock_context, "/invalid/path", "content")

        assert "Error [file_path_resolution_error]" in result
        assert "Error resolving path" in result

    def test_write_file_is_directory_error(self, tmp_path, mock_context):
        """Test that writing to directory returns clear error."""
        dir_path = tmp_path / "directory"
        dir_path.mkdir()

        result = write_file(mock_context, str(dir_path), "content")

        assert "Error [file_write_is_directory]" in result
        assert "Path is a directory" in result

    def test_write_file_permission_error(self, tmp_path, mock_context):
        """Test that PermissionError during write is handled."""
        file_path = tmp_path / "protected.txt"
        with patch.object(Path, "write_text", side_effect=PermissionError("Permission denied")):
            result = write_file(mock_context, str(file_path), "content")

        assert "Error [file_write_permission_denied]" in result
        assert "Permission denied" in result

    def test_write_file_os_error(self, tmp_path, mock_context):
        """Test that general OSError during write is handled."""
        file_path = tmp_path / "fail.txt"
        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            result = write_file(mock_context, str(file_path), "content")

        assert "Error [file_write_os_error]" in result
        assert "Disk full" in result

    def test_write_file_diff_disabled(self, tmp_path, mock_context):
        """Test that diff is suppressed when DIFF_ENABLED=False."""
        from meto.conf import settings

        file_path = tmp_path / "test.txt"
        file_path.write_text("old")

        with patch.object(settings, "DIFF_ENABLED", False):
            result = write_file(mock_context, str(file_path), "new")

        assert "---" not in result
        assert "+++" not in result
        assert "Updated" in result


class TestBinaryDetectionExtra:
    """Extra tests for binary detection edge cases."""

    def test_is_binary_empty_bytes(self):
        from meto.agent.tools.file_tools import is_binary_content

        assert is_binary_content(b"") is False

    def test_is_binary_mixed_content(self):
        from meto.agent.tools.file_tools import is_binary_content

        # Mostly text but with some binary-ish bytes
        content = b"Some text\x01\x02\x03 and more text"
        # 3 non-text bytes in 23 total bytes = 13% < 30%
        assert is_binary_content(content) is False

        # Mostly binary
        content = b"text" + b"\x01\x02\x03\x04\x05\x06\x07\x08"
        # 8 non-text bytes in 12 total bytes = 66% > 30%
        assert is_binary_content(content) is True

    def test_is_binary_large_binary(self):
        from meto.agent.tools.file_tools import is_binary_content

        content = b"\x01" * 10000
        assert is_binary_content(content) is True

    def test_is_binary_error_handling(self):
        from meto.agent.tools.file_tools import is_binary_content

        # Should return True (fail-safe binary) on error
        assert is_binary_content(None) is True  # type: ignore

    def test_write_empty_binary_file_handling(self, tmp_path, mock_context):
        """Test handling of existing empty binary file."""
        file_path = tmp_path / "empty.bin"
        file_path.write_bytes(b"")

        # Mock is_binary_content to return True for this test
        with patch("meto.agent.tools.file_tools.is_binary_content", return_value=True):
            result = write_file(mock_context, str(file_path), "new")

        assert "Updated binary file" in result
        assert "0.0 B → New: 3.0 B" in result
