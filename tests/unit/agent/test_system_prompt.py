from unittest.mock import patch
from meto.agent.system_prompt import SystemPromptBuilder

def test_render_subagents_filters_promoted():
    features = ["subagents"]
    builder = SystemPromptBuilder(features)
    
    # Mock get_agents to return one promoted and one not promoted agent
    mock_agents = {
        "promoted_agent": {
            "description": "promoted",
            "promoted": True
        },
        "not_promoted_agent": {
            "description": "not promoted",
            "promoted": False
        }
    }
    
    with patch("meto.agent.system_prompt.get_agents", return_value=mock_agents):
        prompt = builder.render_subagents()
        assert "promoted_agent" in prompt
        assert "promoted" in prompt
        assert "not_promoted_agent" not in prompt


def test_render_skills_filters_promoted():
    features = ["skills"]
    builder = SystemPromptBuilder(features)
    
    # Mock get_skill_loader to return one promoted and one not promoted skill
    mock_skills = {
        "promoted_skill": {
            "description": "promoted",
            "promoted": True
        },
        "not_promoted_skill": {
            "description": "not promoted",
            "promoted": False
        }
    }
    
    with patch("meto.agent.system_prompt.get_skill_loader") as mock_get_loader:
        mock_loader = mock_get_loader.return_value
        mock_loader.get_resources.return_value = mock_skills
        
        prompt = builder.render_skills()
        assert "promoted_skill" in prompt
        assert "promoted" in prompt
        assert "not_promoted_skill" not in prompt
