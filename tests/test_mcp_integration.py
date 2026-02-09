import pytest
import asyncio
import sys
import os
from julio.mcp_manager import MCPManager
from julio.config import MCPServerConfig

@pytest.mark.asyncio
async def test_mcp_manager_integration():
    # Configure the mock MCP server
    server_script = os.path.abspath("tests/mock_mcp_server.py")
    config = MCPServerConfig(
        name="mock",
        type="stdio",
        command=sys.executable,
        args=[server_script]
    )

    manager = MCPManager([config])
    await manager.start()

    try:
        # Give it a moment to connect and fetch tools
        # The manager has a keep-alive loop that fetches tools every 30s,
        # but get_tools() should trigger an immediate fetch if not in cache.
        tools = await manager.get_tools()

        assert len(tools) > 0
        assert any(t["name"] == "mock_echo" for t in tools)

        # Test that it's cached
        tools2 = await manager.get_tools()
        assert tools == tools2

    finally:
        await manager.stop()

@pytest.mark.asyncio
async def test_mcp_manager_reconnect():
    # Test how manager handles a server that is not immediately available or dies
    # We can use a command that fails
    config = MCPServerConfig(
        name="failing",
        type="stdio",
        command="false",
        args=[]
    )

    manager = MCPManager([config])
    await manager.start()

    try:
        tools = await manager.get_tools()
        assert len(tools) == 0
    finally:
        await manager.stop()
