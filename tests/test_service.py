import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from main import AgentService

@pytest.mark.asyncio
async def test_agent_service():
    with patch('main.load_config') as mock_load_config, \
         patch('main.Persistence') as mock_persistence, \
         patch('main.MessageBus', return_value=AsyncMock()) as mock_bus, \
         patch('main.MCPManager', return_value=AsyncMock()) as mock_mcp, \
         patch('main.SkillsLoader') as mock_skills, \
         patch('main.Agent') as mock_agent:

        # Setup config mock
        config = MagicMock()
        config.db_path = "db"
        config.redis_url = "redis"
        config.mcp_servers = []
        config.skills_path = "skills"
        config.heartbeat_interval_minutes = 0.001 # very short for test
        mock_load_config.return_value = config

        service = AgentService()

        # Test command handling
        mock_agent_instance = mock_agent.return_value
        mock_agent_instance.process_command = AsyncMock(return_value={"resp": "ok"})

        await service._handle_command({"source_id": "s", "user_id": "u", "content": "c"})

        mock_agent_instance.process_command.assert_called()
        mock_bus.return_value.publish_response.assert_called()

        # Test start/stop (briefly)
        # We'll use a timeout to avoid hanging if the service doesn't stop
        service.stop_event = MagicMock()
        service.stop_event.wait = AsyncMock()

        # Mock heartbeat_loop to exit immediately
        service.heartbeat_loop = AsyncMock()

        await service.start()
        mock_mcp.return_value.start.assert_called()
        mock_bus.return_value.subscribe_to_commands.assert_called()

        await service.stop()
        mock_mcp.return_value.stop.assert_called()
        mock_bus.return_value.stop.assert_called()
