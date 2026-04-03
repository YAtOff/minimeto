from pathlib import Path
from unittest.mock import patch

from meto.agent.loaders.agent_loader import AgentLoader
from meto.agent.loaders.skill_loader import SkillLoader


def test_agent_promoted_default(tmp_path):
    # Setup: Create an agent file
    custom_agent_file = tmp_path / "custom.md"
    custom_agent_file.write_text("---\ndescription: custom agent\ntools: [shell]\nprompt: test\n---\nBody")

    loader = AgentLoader(tmp_path)
    loader.discover()

    # Custom agent should not be promoted by default
    assert loader.get_agent_config("custom")["promoted"] is False


def test_agent_promoted_explicit(tmp_path):
    # Setup: Create an agent file with explicit promoted: true
    promoted_agent_file = tmp_path / "promoted.md"
    promoted_agent_file.write_text("---\ndescription: promoted agent\ntools: [shell]\nprompt: test\npromoted: true\n---\nBody")

    loader = AgentLoader(tmp_path)
    loader.discover()

    # Should be promoted as explicitly set
    assert loader.get_agent_config("promoted")["promoted"] is True


def test_agent_promoted_builtin(tmp_path):
    # Mock settings.DEFAULT_RESOURCES_DIR to point to tmp_path
    with patch("meto.agent.loaders.agent_loader.settings") as mock_settings:
        mock_settings.DEFAULT_RESOURCES_DIR = tmp_path
        
        builtin_agents_dir = tmp_path / "agents"
        builtin_agents_dir.mkdir()
        builtin_agent_file = builtin_agents_dir / "builtin.md"
        builtin_agent_file.write_text("---\ndescription: builtin agent\ntools: [shell]\nprompt: test\n---\nBody")

        loader = AgentLoader(builtin_agents_dir)
        loader.discover()

        # Built-in agent should be promoted by default
        assert loader.get_agent_config("builtin")["promoted"] is True


def test_skill_promoted_default(tmp_path):
    # Setup: Create a skill directory
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\ndescription: Test skill\n---\nBody")

    loader = SkillLoader(tmp_path)
    
    # Skills should be promoted by default
    assert loader.get_skill_config("test_skill")["promoted"] is True


def test_skill_promoted_explicit_false(tmp_path):
    # Setup: Create a skill directory with explicit promoted: false
    skill_dir = tmp_path / "not_promoted_skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\ndescription: Not promoted\npromoted: false\n---\nBody")

    loader = SkillLoader(tmp_path)
    
    # Should not be promoted as explicitly set
    assert loader.get_skill_config("not_promoted_skill")["promoted"] is False
