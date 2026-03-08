"""FastMCP client integration for runtime tool discovery."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

from fastmcp import Client

from meto.agent.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

_is_initialized = False


def _config_path() -> Path:
    return Path.cwd() / ".meto/mcp.json"


def _load_config(path: Path) -> dict[str, Any] | None:
    """Load and validate the MCP configuration from mcp.json.

    Args:
        path: Path to the mcp.json file.

    Returns:
        The loaded configuration or None if the file does not exist.

    Raises:
        OSError: If there's an error reading the file.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the configuration is not a dictionary.
    """
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        config = json.load(file)

    if not isinstance(config, dict):
        raise ValueError("mcp.json must contain a JSON object")

    servers = config.get("mcpServers")
    if isinstance(servers, dict):
        for server in servers.values():
            if isinstance(server, dict):
                env = server.get("env")
                if not isinstance(env, dict):
                    env = {}
                    server["env"] = env
                env.setdefault("PATH", os.environ.get("PATH", ""))

    return config


def _render_tool_result(result: Any) -> str:
    if bool(getattr(result, "is_error", False)):
        lines: list[str] = []
        for block in getattr(result, "content", []):
            text = getattr(block, "text", None)
            lines.append(str(text if text is not None else block))
        message = "\n".join(lines).strip()
        return message or "Error: MCP tool call failed"

    structured = getattr(result, "structured_content", None)
    if structured is not None:
        return json.dumps(structured, ensure_ascii=False, default=str)

    data = getattr(result, "data", None)
    if data is not None:
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=False, default=str)

    lines = []
    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        lines.append(str(text if text is not None else block))
    return "\n".join(lines).strip() or ""


def _call_tool_sync(config: dict[str, Any], tool_name: str, arguments: dict[str, Any]) -> str:
    async def _run() -> str:
        async with Client(config) as client:
            result = await client.call_tool(tool_name, arguments, raise_on_error=False)
        return _render_tool_result(result)

    return asyncio.run(_run())


def _discover_server(
    server_name: str, server_config: dict[str, Any]
) -> tuple[list[Any], str | None]:
    """Discover tools from a single MCP server config entry.

    Returns a tuple of (tools, error_message). On success error_message is None.
    """
    single_server_config = {"mcpServers": {server_name: server_config}}

    async def _run() -> list[Any]:
        async with Client(single_server_config) as client:
            return list(await client.list_tools())

    try:
        tools = asyncio.run(_run())
        return tools, None
    except Exception as exc:
        logger.error(f"Failed to discover MCP tools for {server_name}: {exc}")
        return [], f"{server_name}: {exc}"


def initialize_mcp_registry(registry: ToolRegistry) -> str | None:
    """Initialize MCP tools from ``{CWD}/mcp.json`` into the runtime registry.

    Iterates each server independently so a single failing server does not
    prevent tools from other servers being registered.

    Returns:
            Optional warning/error message. ``None`` means success or no config file.
    """

    global _is_initialized

    if _is_initialized:
        return None

    config_file = _config_path()
    try:
        config = _load_config(config_file)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _is_initialized = True
        error_msg = f"MCP initialization failed: {exc}"
        logger.error(error_msg)
        return error_msg

    if config is None:
        return None

    mcp_servers: dict[str, Any] = config.get("mcpServers") or {}
    errors: list[str] = []

    for server_name, server_config in mcp_servers.items():
        tools, error = _discover_server(server_name, server_config)
        if error:
            errors.append(error)
            continue

        # Build a per-server config so call_tool routes to the right process.
        single_server_config: dict[str, Any] = {"mcpServers": {server_name: server_config}}
        # Tools returned from a single-server config carry no prefix; strip any
        # server prefix FastMCP may have added before registering.
        registry.register_from_mcp(
            tools,
            lambda tool_name, parameters, _cfg=single_server_config: _call_tool_sync(
                _cfg, tool_name, parameters
            ),
        )

    _is_initialized = True
    if errors:
        msg = "MCP tool discovery warnings:\n" + "\n".join(f"  - {e}" for e in errors)
        logger.warning(msg)
        return msg

    return None
