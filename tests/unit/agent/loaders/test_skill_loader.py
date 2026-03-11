import json
from unittest.mock import patch

import pytest

from meto.agent.loaders.skill_loader import SkillLoader


class MockMemoryError(BaseException):
    """A mock memory error that is not Exception but BaseException (like real MemoryError)
    Actually real MemoryError IS an Exception.
    Let's check:
    >>> issubclass(MemoryError, Exception)
    True

    Wait, the goal was to NOT catch unrelated errors like MemoryError.
    If the reviewer said 'like MemoryError', they might have meant that catching EVERYTHING is bad.
    """

    pass


def test_get_skill_content_bubbles_up_unexpected_exception(tmp_path):
    # Setup: Create a skill directory and SKILL.md
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\ndescription: Test skill\n---\nBody")

    loader = SkillLoader(tmp_path)

    # Verify skill is discovered
    assert "test_skill" in loader.list_skills()

    # Mock parse_resource_file to raise an unexpected exception
    # Use RuntimeError which is NOT in the caught exceptions (OSError, ValueError, json.JSONDecodeError)
    with patch.object(
        SkillLoader, "parse_resource_file", side_effect=RuntimeError("Unexpected error")
    ):
        with pytest.raises(RuntimeError, match="Unexpected error"):
            loader.get_skill_content("test_skill")


def test_get_skill_content_catches_expected_exceptions(tmp_path):
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\ndescription: Test skill\n---\nBody")

    loader = SkillLoader(tmp_path)

    # OSError should be caught and re-raised as ValueError
    with patch.object(SkillLoader, "parse_resource_file", side_effect=OSError("Disk error")):
        with pytest.raises(ValueError, match="Failed to load skill 'test_skill'"):
            loader.get_skill_content("test_skill")

    # ValueError should be caught and re-raised as ValueError
    with patch.object(SkillLoader, "parse_resource_file", side_effect=ValueError("Parse error")):
        with pytest.raises(ValueError, match="Failed to load skill 'test_skill'"):
            loader.get_skill_content("test_skill")


def test_get_skill_content_catches_json_error(tmp_path):
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\ndescription: Test skill\n---\nBody")

    loader = SkillLoader(tmp_path)

    # json.JSONDecodeError should be caught and re-raised as ValueError
    # Need to provide some valid-ish args to JSONDecodeError
    json_err = json.JSONDecodeError("Expecting value", "{}", 0)
    with patch.object(SkillLoader, "parse_resource_file", side_effect=json_err):
        with pytest.raises(ValueError, match="Failed to load skill 'test_skill'"):
            loader.get_skill_content("test_skill")


def test_skill_discovery_reports_errors(tmp_path, caplog):
    # Setup: Create a bad skill directory
    bad_skill_dir = tmp_path / "bad_skill"
    bad_skill_dir.mkdir()
    bad_skill_file = bad_skill_dir / "SKILL.md"
    # Invalid YAML
    bad_skill_file.write_text("---\ndescription: [unclosed\n---\nBody")

    import logging

    with caplog.at_level(logging.WARNING):
        loader = SkillLoader(tmp_path)

    # Verify summary warning is logged
    assert "Failed to parse 1 resource files during discovery" in caplog.text
    assert str(bad_skill_file) in caplog.text
    assert "bad_skill" not in loader.list_skills()
