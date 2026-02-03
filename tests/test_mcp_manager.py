import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from mcp_manager import MCPManager

@pytest.mark.asyncio
async def test_mcp_manager_list_tools():
    # Mock server config
    mock_cfg = MagicMock()
    mock_cfg.name = "test_server"
    mock_cfg.type = "stdio"
    mock_cfg.command = "echo"
    mock_cfg.args = []

    mock_tool = MagicMock()
    mock_tool.name = 'test_server_tool1'
    # Mock _get_declaration for the new implementation
    mock_decl = MagicMock()
    mock_decl.model_dump.return_value = {'name': 'test_server_tool1', 'description': 'desc'}
    mock_tool._get_declaration.return_value = mock_decl

    mock_toolset = MagicMock()
    mock_toolset.get_tools = AsyncMock(return_value=[mock_tool])

    with patch('mcp_manager.McpToolset', return_value=mock_toolset):
        manager = MCPManager([mock_cfg])
        tools = await manager.list_tools()

        assert len(tools) == 1
        assert tools[0]['name'] == 'test_server_tool1'
        mock_toolset.get_tools.assert_called()

@pytest.mark.asyncio
async def test_mcp_manager_parallel_get_tools():
    mock_cfg1 = MagicMock()
    mock_cfg1.name = "s1"
    mock_cfg1.type = "sse"
    mock_cfg1.url = "http://s1"

    mock_cfg2 = MagicMock()
    mock_cfg2.name = "s2"
    mock_cfg2.type = "sse"
    mock_cfg2.url = "http://s2"

    async def s1(*args):
        await asyncio.sleep(0.1)
        return ["t1"]

    async def s2(*args):
        await asyncio.sleep(0.1)
        return ["t2"]

    mock_toolset1 = MagicMock()
    mock_toolset1.get_tools = AsyncMock(side_effect=s1)
    mock_toolset1.close = AsyncMock()

    mock_toolset2 = MagicMock()
    mock_toolset2.get_tools = AsyncMock(side_effect=s2)
    mock_toolset2.close = AsyncMock()

    with patch('mcp_manager.McpToolset') as mock_ts_cls:
        mock_ts_cls.side_effect = [mock_toolset1, mock_toolset2]

        manager = MCPManager([mock_cfg1, mock_cfg2])

        import time
        start = time.perf_counter()
        tools = await manager.get_tools()
        end = time.perf_counter()

        assert len(tools) == 2
        assert "t1" in tools
        assert "t2" in tools
        # Should take ~0.1s, not ~0.2s
        assert end - start < 0.2 # Buffer for CI

        await manager.close()
        mock_toolset1.close.assert_called_once()
        mock_toolset2.close.assert_called_once()
