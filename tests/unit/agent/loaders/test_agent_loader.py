import logging

from meto.agent.loaders.agent_loader import AgentLoader


def test_agent_discovery_reports_errors(tmp_path, caplog):
    # Setup: Create a bad agent file
    bad_agent_file = tmp_path / "bad.md"
    # Invalid YAML
    bad_agent_file.write_text("---\ndescription: [unclosed\n---\nBody")

    loader = AgentLoader(tmp_path)

    with caplog.at_level(logging.WARNING):
        loader.discover()

    # Verify summary warning is logged
    assert "Failed to parse 1 resource files during discovery" in caplog.text
    assert str(bad_agent_file) in caplog.text
    assert "bad" not in loader.list_agents()


def test_agent_discovery_loads_good_agent(tmp_path):
    # Setup: Create a good agent file
    good_agent_file = tmp_path / "good.md"
    good_agent_file.write_text("---\ndescription: ok\ntools: [shell]\nprompt: test\n---\nBody")

    loader = AgentLoader(tmp_path)
    loader.discover()

    assert "good" in loader.list_agents()
