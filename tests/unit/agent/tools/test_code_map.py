from meto.agent.context import Context
from meto.agent.todo import TodoManager
from meto.agent.tools.file_tools import detect_lang, get_code_map, read_file


def test_detect_lang():
    assert detect_lang("test.py") == "python"
    assert detect_lang("test.js") == "javascript"
    assert detect_lang("test.ts") == "typescript"
    assert detect_lang("test.txt") is None


def test_code_map_python(tmp_path):
    py_file = tmp_path / "test.py"
    # Note: Leading newline makes 'class MyClass' start at line 2
    py_file.write_text(
        """
class MyClass:
    def __init__(self):
        pass

def my_func():
    return 1
""",
        encoding="utf-8",
    )

    code_map = get_code_map(py_file, "python")
    # Tree-sitter 0.21.x line ranges for this content:
    assert "[CLASS] MyClass (Lines 2-4)" in code_map
    assert "[FUNC] __init__ (Lines 3-4)" in code_map
    assert "[FUNC] my_func (Lines 6-7)" in code_map


def test_read_file_intercepts_large_file(tmp_path):
    # Create a "large" file (more than 600 lines)
    large_file = tmp_path / "large.py"
    content = "class A:\n    pass\n" + "\n" * 650 + "def f():\n    pass\n"
    large_file.write_text(content, encoding="utf-8")

    # Mock context
    ctx = Context(todos=TodoManager())

    # Reading without bounds should return the map
    result = read_file(ctx, str(large_file))
    assert "FILE TOO LARGE" in result
    assert "structural map" in result
    assert "[CLASS] A (Lines 1-2)" in result
    assert "[FUNC] f (Lines 653-654)" in result
    assert "Use read_file(path, start_line, end_line) to read a specific range." in result


def test_read_file_no_intercept_small_file(tmp_path):
    small_file = tmp_path / "small.py"
    small_file.write_text("def f():\n    pass\n", encoding="utf-8")

    ctx = Context(todos=TodoManager())
    result = read_file(ctx, str(small_file))
    assert "1 | def f():" in result
    assert "FILE TOO LARGE" not in result
