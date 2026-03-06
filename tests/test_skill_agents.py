"""Tests for skill-local agents functionality."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from meto.agent.agent import Agent
from meto.agent.context import Context
from meto.agent.exceptions import SkillAgentNotFoundError, SkillAgentValidationError
from meto.agent.loaders.skill_loader import SkillLoader, clear_skill_cache
from meto.agent.todo import TodoManager
from meto.agent.tools.skill_tools import load_agent as _load_agent


@pytest.fixture
def temp_skill_dir(tmp_path: Path) -> Path:
    """Create a temporary skill directory with agents."""
    skill_dir = tmp_path / "test_skill"
    skill_dir.mkdir()

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        """---
name: test_skill
description: A test skill
---
This is a test skill content.
""",
        encoding="utf-8",
    )

    # Create agents subdirectory
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir()

    # Create a valid agent file
    agent_file = agents_dir / "reviewer.md"
    agent_file.write_text(
        """---
name: reviewer
description: Code reviewer agent
tools:
  - read_file
  - grep_search
---
This agent reviews code.
""",
        encoding="utf-8",
    )

    # Create another agent file
    agent_file2 = agents_dir / "tester.md"
    agent_file2.write_text(
        """---
name: tester
description: Testing agent
tools: [read_file, write_file]
---
This agent tests code.
""",
        encoding="utf-8",
    )

    return skill_dir


@pytest.fixture
def skill_loader(temp_skill_dir: Path) -> SkillLoader:
    """Create a SkillLoader instance with a test skill."""
    clear_skill_cache()
    return SkillLoader(temp_skill_dir.parent)


class TestSkillLoaderAgentsDir:
    """Tests for SkillLoader.get_skill_agents_dir()."""

    def test_get_skill_agents_dir_exists(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agents directory when it exists."""
        agents_dir = skill_loader.get_skill_agents_dir("test_skill")
        assert agents_dir is not None
        assert agents_dir.name == "agents"
        assert agents_dir.is_dir()

    def test_get_skill_agents_dir_missing_skill(self, skill_loader: SkillLoader) -> None:
        """Test getting agents directory for non-existent skill."""
        agents_dir = skill_loader.get_skill_agents_dir("nonexistent")
        assert agents_dir is None

    def test_get_skill_agents_dir_no_agents_folder(self, tmp_path: Path) -> None:
        """Test getting agents directory when skill has no agents folder."""
        # Create skill without agents folder
        skill_dir = tmp_path / "no_agents_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no_agents_skill\ndescription: No agents\n---\nContent",
            encoding="utf-8",
        )

        loader = SkillLoader(tmp_path)
        agents_dir = loader.get_skill_agents_dir("no_agents_skill")
        assert agents_dir is None


class TestSkillLoaderListAgents:
    """Tests for SkillLoader.list_skill_agents()."""

    def test_list_skill_agents(self, skill_loader: SkillLoader) -> None:
        """Test listing agents in a skill."""
        agents = skill_loader.list_skill_agents("test_skill")
        assert sorted(agents) == ["reviewer", "tester"]

    def test_list_skill_agents_empty(self, skill_loader: SkillLoader, tmp_path: Path) -> None:
        """Test listing agents when skill has no agents folder."""
        skill_dir = tmp_path / "empty_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: empty_skill\ndescription: Empty\n---\nContent",
            encoding="utf-8",
        )

        agents = skill_loader.list_skill_agents("empty_skill")
        assert agents == []

    def test_list_skill_agents_missing_skill(self, skill_loader: SkillLoader) -> None:
        """Test listing agents for non-existent skill."""
        agents = skill_loader.list_skill_agents("nonexistent")
        assert agents == []


class TestSkillLoaderGetAgentConfig:
    """Tests for SkillLoader.get_skill_agent_config()."""

    def test_get_skill_agent_config_valid(self, skill_loader: SkillLoader) -> None:
        """Test getting valid agent configuration."""
        config = skill_loader.get_skill_agent_config("test_skill", "reviewer")
        assert config["name"] == "reviewer"
        assert config["description"] == "Code reviewer agent"
        assert config["tools"] == ["read_file", "grep_search"]
        assert "This agent reviews code" in config["prompt"]

    def test_get_skill_agent_config_missing_skill(self, skill_loader: SkillLoader) -> None:
        """Test getting agent config for non-existent skill."""
        with pytest.raises(SkillAgentNotFoundError) as exc_info:
            skill_loader.get_skill_agent_config("nonexistent", "reviewer")
        assert "Skill 'nonexistent' not found" in str(exc_info.value)

    def test_get_skill_agent_config_no_agents_folder(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agent config when skill has no agents folder."""
        # Create a new skill without agents folder in the same parent dir as test_skill
        skill_dir = temp_skill_dir.parent / "no_agents_skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: no_agents_skill\ndescription: No agents\n---\nContent",
            encoding="utf-8",
        )

        # Recreate loader to discover the new skill
        from meto.agent.loaders.skill_loader import clear_skill_cache

        clear_skill_cache()
        new_loader = SkillLoader(temp_skill_dir.parent)

        with pytest.raises(SkillAgentNotFoundError) as exc_info:
            new_loader.get_skill_agent_config("no_agents_skill", "reviewer")
        assert "no agents directory" in str(exc_info.value).lower()

    def test_get_skill_agent_config_missing_agent(self, skill_loader: SkillLoader) -> None:
        """Test getting config for non-existent agent."""
        with pytest.raises(SkillAgentNotFoundError) as exc_info:
            skill_loader.get_skill_agent_config("test_skill", "nonexistent")
        assert "Agent 'nonexistent' not found in skill 'test_skill'" in str(exc_info.value)
        assert "Available agents:" in str(exc_info.value)

    def test_get_skill_agent_config_invalid_no_description(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agent config with missing description."""
        agent_file = temp_skill_dir / "agents" / "invalid.md"
        agent_file.write_text(
            """---
name: invalid
tools: [read_file]
---
Content""",
            encoding="utf-8",
        )

        with pytest.raises(SkillAgentValidationError) as exc_info:
            skill_loader.get_skill_agent_config("test_skill", "invalid")
        assert "validation errors" in str(exc_info.value).lower()

    def test_get_skill_agent_config_invalid_empty_tools(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agent config with empty tools list."""
        agent_file = temp_skill_dir / "agents" / "invalid.md"
        agent_file.write_text(
            """---
name: invalid
description: Invalid agent
tools: []
---
Content""",
            encoding="utf-8",
        )

        with pytest.raises(SkillAgentValidationError) as exc_info:
            skill_loader.get_skill_agent_config("test_skill", "invalid")
        assert "validation errors" in str(exc_info.value).lower()

    def test_get_skill_agent_config_invalid_unknown_tool(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agent config with unknown tool."""
        agent_file = temp_skill_dir / "agents" / "invalid.md"
        agent_file.write_text(
            """---
name: invalid
description: Invalid agent
tools: [nonexistent_tool]
---
Content""",
            encoding="utf-8",
        )

        with pytest.raises(SkillAgentValidationError) as exc_info:
            skill_loader.get_skill_agent_config("test_skill", "invalid")
        assert "Unknown tool" in str(exc_info.value)

    def test_get_skill_agent_config_invalid_yaml(
        self, skill_loader: SkillLoader, temp_skill_dir: Path
    ) -> None:
        """Test getting agent config with invalid YAML."""
        agent_file = temp_skill_dir / "agents" / "invalid.md"
        # Write invalid YAML (missing closing bracket for tools list)
        agent_file.write_text(
            """---
name: invalid
description: Invalid agent
tools: [unclosed list
---
Content""",
            encoding="utf-8",
        )

        # The YAML parser may raise various exceptions, so we catch the validation error
        # that occurs when parsing fails
        with pytest.raises((SkillAgentValidationError, ValueError)):
            skill_loader.get_skill_agent_config("test_skill", "invalid")


class TestLoadAgentTool:
    """Tests for the load_agent tool."""

    def test_load_agent_no_active_skill(self, skill_loader: SkillLoader) -> None:
        """Test load_agent when no skill is active."""
        context = Context(todos=TodoManager(), history=[])
        result = _load_agent(context, "reviewer")
        assert "Error: No skill is currently active" in result
        assert "Use load_skill first" in result

    def test_load_agent_success(self, skill_loader: SkillLoader, temp_skill_dir: Path) -> None:
        """Test load_agent with active skill."""
        context = Context(todos=TodoManager(), history=[])
        context.active_skill = "test_skill"

        # Patch get_skill_loader to return our test loader
        # get_skill_loader() returns a SkillLoader, so we return skill_loader directly
        with patch("meto.agent.loaders.skill_loader.get_skill_loader", return_value=skill_loader):
            # Need to patch at call site
            with patch("meto.agent.tools.skill_tools.get_skill_loader", return_value=skill_loader):
                result = _load_agent(context, "reviewer")
                assert "Code reviewer agent" in result
                assert "read_file" in result

    def test_load_agent_not_found(self, skill_loader: SkillLoader) -> None:
        """Test load_agent with non-existent agent."""
        context = Context(todos=TodoManager(), history=[])
        context.active_skill = "test_skill"

        with patch("meto.agent.loaders.skill_loader.get_skill_loader", return_value=skill_loader):
            with patch("meto.agent.tools.skill_tools.get_skill_loader", return_value=skill_loader):
                result = _load_agent(context, "nonexistent")
                assert "Error:" in result
                assert "Available agents:" in result


class TestAgentSubagentWithSkill:
    """Tests for Agent.subagent() with skill_name parameter."""

    def test_subagent_with_skill_name(self, skill_loader: SkillLoader) -> None:
        """Test creating subagent from skill-local agent."""
        with patch("meto.agent.loaders.skill_loader.get_skill_loader", return_value=skill_loader):
            agent = Agent.subagent("reviewer", skill_name="test_skill")
            assert agent.name == "reviewer"
            assert "This agent reviews code" in agent.prompt
            assert "read_file" in agent.tool_names
            assert "grep_search" in agent.tool_names

    def test_subagent_falls_back_to_global(self, skill_loader: SkillLoader) -> None:
        """Test that subagent falls back to global agents when skill agent not found."""
        # Create a global agent
        global_agents_dir = Path(__file__).parent.parent / ".meto" / "agents"
        global_agents_dir.mkdir(parents=True, exist_ok=True)
        global_agent_file = global_agents_dir / "global_test.md"
        global_agent_file.write_text(
            """---
name: global_test
description: Global test agent
tools: [read_file]
---
Global agent content.""",
            encoding="utf-8",
        )

        try:
            with patch(
                "meto.agent.loaders.skill_loader.get_skill_loader", return_value=skill_loader
            ):
                agent = Agent.subagent("global_test", skill_name="test_skill")
                assert agent.name == "global_test"
        finally:
            # Cleanup
            global_agent_file.unlink()

    def test_subagent_skill_not_found_falls_back(self, skill_loader: SkillLoader) -> None:
        """Test that subagent falls back to global when skill doesn't have the agent."""
        with patch("meto.agent.loaders.skill_loader.get_skill_loader", return_value=skill_loader):
            # This should fall back to global agents
            # If global_test doesn't exist, it will raise SubagentError
            try:
                Agent.subagent("global_test", skill_name="test_skill")
            except Exception as e:
                # Expected if global_test doesn't exist
                assert "Unknown agent type" in str(e)
