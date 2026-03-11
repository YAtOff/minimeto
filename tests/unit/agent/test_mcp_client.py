import json
from unittest.mock import patch

import pytest

from meto.agent.exceptions import MCPInitializationError
from meto.agent.mcp_client import initialize_mcp_registry
from meto.agent.tool_registry import ToolRegistry


@pytest.fixture
def registry():
    return ToolRegistry()


def test_initialize_mcp_registry_invalid_config(registry, tmp_path, caplog):
    mcp_json = tmp_path / "mcp.json"
    mcp_json.write_text("invalid json")

    with patch("meto.agent.mcp_client._config_path", return_value=mcp_json):
        # We need to reset the global _is_initialized for testing
        with patch("meto.agent.mcp_client._is_initialized", False):
            with caplog.at_level("ERROR"):
                with pytest.raises(MCPInitializationError) as excinfo:
                    initialize_mcp_registry(registry)
                assert "MCP initialization failed" in str(excinfo.value)
                assert any(
                    "MCP initialization failed" in record.message for record in caplog.records
                )


def test_initialize_mcp_registry_server_failure(registry, tmp_path, caplog):
    mcp_json = tmp_path / "mcp.json"
    config = {"mcpServers": {"fail-server": {"command": "nonexistent"}}}
    mcp_json.write_text(json.dumps(config))

    with patch("meto.agent.mcp_client._config_path", return_value=mcp_json):
        with patch("meto.agent.mcp_client._is_initialized", False):
            with caplog.at_level("ERROR"):
                # _discover_server will fail because "nonexistent" command won't work
                with pytest.raises(MCPInitializationError) as excinfo:
                    initialize_mcp_registry(registry)
                assert "MCP tool discovery failed for all 1 servers" in str(excinfo.value)
                assert "fail-server" in str(excinfo.value)
                # Success count should be 0/1, which shows as "all 1 servers"
                assert "0/1" not in str(excinfo.value)


def test_initialize_mcp_registry_partial_failure(registry, tmp_path):
    mcp_json = tmp_path / "mcp.json"
    # Configuration with two servers
    config = {
        "mcpServers": {"fail-server": {"command": "nonexistent"}, "ok-server": {"command": "echo"}}
    }
    mcp_json.write_text(json.dumps(config))

    with patch("meto.agent.mcp_client._config_path", return_value=mcp_json):
        with patch("meto.agent.mcp_client._is_initialized", False):
            # Mock _discover_server for ok-server to return dummy tools
            with patch("meto.agent.mcp_client._discover_server") as mock_discover:

                def side_effect(name, cfg):
                    if name == "ok-server":
                        return [{"name": "test_tool"}], None
                    return [], f"{name}: some error"

                mock_discover.side_effect = side_effect

                with pytest.raises(MCPInitializationError) as excinfo:
                    initialize_mcp_registry(registry)

                assert "MCP tool discovery partially failed (1/2 servers loaded)" in str(
                    excinfo.value
                )
                assert "fail-server: some error" in str(excinfo.value)
