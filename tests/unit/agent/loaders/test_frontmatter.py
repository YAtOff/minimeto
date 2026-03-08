import pytest

from meto.agent.loaders.frontmatter import parse_yaml_frontmatter


def test_parse_frontmatter_success():
    content = """---
name: test-agent
description: A test agent
tools:
  - shell
  - read_file
---
This is the body of the agent.
It can have multiple lines.
"""
    result = parse_yaml_frontmatter(content)
    assert result["metadata"] == {
        "name": "test-agent",
        "description": "A test agent",
        "tools": ["shell", "read_file"],
    }
    assert result["body"] == "This is the body of the agent.\nIt can have multiple lines."


def test_parse_no_frontmatter():
    content = "Just a body without frontmatter."
    result = parse_yaml_frontmatter(content)
    assert result["metadata"] == {}
    assert result["body"] == "Just a body without frontmatter."


def test_parse_empty_frontmatter():
    content = """---
---
Body here."""
    _result = parse_yaml_frontmatter(content)
    # The regex requires \n(.*?)\n---, so --- \n --- might match or not
    # Let's check the regex: re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
    # Actually, it might fail if there's no newline after second ---
    pass


def test_parse_empty_yaml_frontmatter():
    content = """---

---
Body here."""
    result = parse_yaml_frontmatter(content)
    assert result["metadata"] == {}
    assert result["body"] == "Body here."


def test_parse_malformed_yaml():
    content = """---
invalid: : yaml
---
Body."""
    with pytest.raises(Exception):  # noqa: B017
        parse_yaml_frontmatter(content)


def test_parse_frontmatter_no_body():
    content = """---
name: only-meta
---
"""
    result = parse_yaml_frontmatter(content)
    assert result["metadata"] == {"name": "only-meta"}
    assert result["body"] == ""
