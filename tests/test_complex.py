import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from mcp_manager import MCPManager
from config import MCPServerConfig
from agent import Agent, AgentConfig
from persistence import Persistence
from skills_loader import SkillsLoader

# MCP Manager Tests
@pytest.mark.asyncio
async def test_mcp_manager():
    configs = [
        MCPServerConfig(name="test-stdio", type="stdio", command="echo"),
        MCPServerConfig(name="test-sse", type="sse", url="http://localhost")
    ]
    manager = MCPManager(configs)

    # Mocking the mcp sdk components is complex, let's mock the start method's dependencies
    with patch('mcp_manager.stdio_client', return_value=AsyncMock()) as mock_stdio, \
         patch('mcp_manager.sse_client', return_value=AsyncMock()) as mock_sse, \
         patch('mcp_manager.ClientSession', return_value=AsyncMock()) as mock_session:

        # We need to simulate the context managers
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        mock_sse.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = session_instance

        await manager.start()
        assert len(manager.sessions) == 2

        # Test list tools
        mock_tool = MagicMock()
        mock_tool.name = "mytool"
        mock_tool.description = "desc"
        mock_tool.inputSchema = {}
        session_instance.list_tools.return_value.tools = [mock_tool]

        tools = await manager.list_tools()
        assert len(tools) == 2 # 1 per server
        assert tools[0]["name"] == "mytool"

        # Test call tool
        await manager.call_tool("test-stdio", "mytool", {})
        session_instance.call_tool.assert_called_with("mytool", {})

        await manager.stop()

# Agent Tests
@pytest.mark.asyncio
async def test_agent():
    config = AgentConfig(gemini_api_key="key")
    persistence = MagicMock(spec=Persistence)
    mcp_manager = MagicMock(spec=MCPManager)
    skills_loader = MagicMock(spec=SkillsLoader)

    persistence.get_history.return_value = []
    skills_loader.load_skills.return_value = "Skills"
    mcp_manager.list_tools.return_value = []

    with patch('google.generativeai.GenerativeModel') as mock_model_class:
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model

        mock_chat = AsyncMock()
        mock_model.start_chat.return_value = mock_chat

        mock_response = MagicMock()
        mock_response.text = "Response [NEEDS_INPUT]"
        mock_chat.send_message_async.return_value = mock_response

        agent = Agent(config, persistence, mcp_manager, skills_loader)

        result = await agent.process_command("source", "user", "Hello")

        assert result["content"] == "Response [NEEDS_INPUT]"
        assert result["needs_input"] is True
        persistence.add_history.assert_any_call("source", "user", "user", "Hello")
        persistence.add_history.assert_any_call("source", "user", "assistant", "Response [NEEDS_INPUT]")
