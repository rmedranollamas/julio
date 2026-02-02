import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from main import AgentService

@pytest.mark.asyncio
async def test_agent_service():
    with patch('main.load_config') as mock_load_config, \
         patch('main.PersistenceWrapper') as mock_persistence, \
         patch('main.MessageBus', return_value=AsyncMock()) as mock_bus, \
         patch('main.SkillsLoader') as mock_skills, \
         patch('main.AgentWrapper') as mock_agent_wrapper, \
         patch('main.Runner', return_value=AsyncMock()) as mock_runner:

        # Setup config mock
        config = MagicMock()
        config.db_path = "db"
        config.redis_url = "redis"
        config.mcp_servers = []
        config.skills_path = "skills"
        config.heartbeat_interval_minutes = 0.001 # very short for test
        mock_load_config.return_value = config

        # Mocking persistence and agent
        mock_persistence_instance = mock_persistence.return_value
        mock_persistence_instance.session_service = MagicMock()

        mock_agent_instance = mock_agent_wrapper.return_value
        mock_agent_instance.agent = MagicMock()
        mock_agent_instance.initialize = AsyncMock()
        mock_agent_instance.run_with_runner = AsyncMock(return_value={"resp": "ok"})

        service = AgentService()
        service.runner = mock_runner.return_value

        # Test command handling
        await service._handle_command({"source_id": "s", "user_id": "u", "content": "c"})

        mock_agent_instance.run_with_runner.assert_called()
        mock_bus.return_value.publish_response.assert_called()

        # Test start/stop (briefly)
        service.stop_event = MagicMock()
        service.stop_event.wait = AsyncMock()

        # Mock heartbeat_loop to exit immediately
        service.heartbeat_loop = AsyncMock()

        await service.start()
        mock_bus.return_value.subscribe_to_commands.assert_called()

        await service.stop()
        mock_bus.return_value.stop.assert_called()
        mock_runner.return_value.close.assert_called()
