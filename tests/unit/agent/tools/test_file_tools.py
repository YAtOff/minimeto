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
    assert result == content


def test_read_file_range(tmp_path, mock_context):
    file_path = tmp_path / "range.txt"
    content = "line1\nline2\nline3\nline4\nline5"
    file_path.write_text(content)

    result = read_file(mock_context, str(file_path), start_line=2, end_line=4)
    assert "lines 2-4" in result
    assert "line2\nline3\nline4" in result
    assert "line1" not in result
    assert "line5" not in result


def test_read_file_not_found(mock_context):
    result = read_file(mock_context, "/non/existent/file")
    assert "Error: File does not exist" in result


def test_write_file_success(tmp_path, mock_context):
    file_path = tmp_path / "new_file.txt"
    content = "new content"

    result = write_file(mock_context, str(file_path), content)
    assert "Successfully wrote" in result
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
