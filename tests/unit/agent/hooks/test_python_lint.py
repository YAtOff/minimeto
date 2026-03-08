import logging
from unittest.mock import patch

from meto.agent.hooks.base import SuccessResult
from meto.agent.hooks.python_lint import PythonLintHook


def test_python_lint_hook_matches():
    # Should match successful write_file on .py file
    hook = PythonLintHook(
        tool_name="write_file",
        arguments={"path": "test.py"},
        output="Successfully wrote to test.py",
    )
    assert hook.matches() is True

    # Should not match non-.py file
    hook = PythonLintHook(
        tool_name="write_file",
        arguments={"path": "test.txt"},
        output="Successfully wrote to test.txt",
    )
    assert hook.matches() is False

    # Should not match failed tool call
    hook = PythonLintHook(
        tool_name="write_file", arguments={"path": "test.py"}, output="Error: Failed to write"
    )
    assert hook.matches() is False

    # Should not match different tool
    hook = PythonLintHook(
        tool_name="read_file", arguments={"path": "test.py"}, output="file content"
    )
    assert hook.matches() is False


def test_python_lint_hook_run_success():
    hook = PythonLintHook(
        tool_name="write_file",
        arguments={"path": "test.py"},
        output="Successfully wrote to test.py",
    )

    with patch("subprocess.run") as mock_run:
        result = hook.run()
        assert isinstance(result, SuccessResult)
        assert mock_run.call_count == 2
        # Verify ruff check --fix and ruff format were called
        mock_run.assert_any_call(
            ["ruff", "check", "--fix", "test.py"],
            check=False,
            capture_output=True,
            text=True,
        )
        mock_run.assert_any_call(
            ["ruff", "format", "test.py"],
            check=False,
            capture_output=True,
            text=True,
        )


def test_python_lint_hook_run_exception(caplog):
    hook = PythonLintHook(
        tool_name="write_file",
        arguments={"path": "test.py"},
        output="Successfully wrote to test.py",
    )

    with patch("subprocess.run", side_effect=Exception("Ruff not found")):
        with caplog.at_level(logging.WARNING):
            result = hook.run()
            assert isinstance(result, SuccessResult)
            assert "Python lint hook failed for test.py: Ruff not found" in caplog.text
