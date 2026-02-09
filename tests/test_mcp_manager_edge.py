import pytest
import logging
from julio.mcp_manager import MCPManager
from julio.config import MCPServerConfig

def test_mcp_manager_init_errors(caplog):
    # Test missing command for stdio
    cfg1 = MCPServerConfig(name="n1", type="stdio", command="", args=[])
    # Test missing url for sse
    cfg2 = MCPServerConfig(name="n2", type="sse", url="", command="", args=[])
    # Test unknown type by using model_construct to bypass validation
    cfg3 = MCPServerConfig.model_construct(name="n3", type="unknown", command="", args=[])

    with caplog.at_level(logging.WARNING):
        manager = MCPManager([cfg1, cfg2, cfg3])
        assert len(manager.managed_servers) == 0
        assert "missing command" in caplog.text
        assert "missing url" in caplog.text
        assert "Unknown MCP server type" in caplog.text

@pytest.mark.asyncio
async def test_mcp_manager_no_servers():
    manager = MCPManager([])
    tools = await manager.get_tools()
    assert tools == []
