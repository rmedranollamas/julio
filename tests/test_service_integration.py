import pytest
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch
from julio.main import AgentService
from google.genai import types

@pytest.mark.asyncio
async def test_agent_service_full_flow(tmp_path):
    db_path = str(tmp_path / "test_service.db")
    config_data = {
        "gemini_api_key": "fake_key",
        "db_path": db_path,
        "skills_path": str(tmp_path / "skills"),
        "mcp_servers": [],
        "heartbeat_interval_minutes": 0.01
    }
    config_file = tmp_path / "agent.json"
    config_file.write_text(json.dumps(config_data))

    os.makedirs(config_data["skills_path"], exist_ok=True)

    service = AgentService(str(config_file))

    # Mock Event
    mock_event = MagicMock()
    mock_event.author = "agent_service"
    mock_event.content = types.Content(role="model", parts=[types.Part(text="Hello from mock agent")])

    async def mock_run_async(*args, **kwargs):
        yield mock_event

    with patch("julio.main.Runner") as MockRunner:
        mock_runner_instance = MockRunner.return_value
        mock_runner_instance.run_async = mock_run_async
        mock_runner_instance.close = AsyncMock()

        # Start service in background task
        service_task = asyncio.create_task(service.start())

        # Wait a bit for initialization
        await asyncio.sleep(0.5)

        # Subscribe to responses to verify
        responses = []
        async def response_callback(msg):
            responses.append(msg)

        await service.bus.subscribe_to_commands("agent_responses", response_callback)

        # Send command
        command = {
            "source_id": "test_source",
            "user_id": "test_user",
            "content": "Say hello"
        }
        await service.bus.publish_response("agent_commands", command)

        # Wait for response
        for _ in range(20):
            await asyncio.sleep(0.1)
            if responses:
                break

        assert len(responses) >= 1
        assert "Hello from mock agent" in responses[0]["content"]
        assert responses[0]["source_id"] == "test_source"

        # Test heartbeat
        # Heartbeat is 0.01 minutes = 0.6 seconds.
        # We should see another response soon.
        responses.clear()
        for _ in range(20):
            await asyncio.sleep(0.1)
            if responses:
                break

        assert len(responses) >= 1
        assert responses[0]["source_id"] == "system_heartbeat"

        # Stop service
        await service.stop()
        await service_task

@pytest.mark.asyncio
async def test_agent_service_stop_cleanup(tmp_path):
    config_file = tmp_path / "agent.json"
    config_data = {
        "gemini_api_key": "fake_key",
        "db_path": str(tmp_path / "test.db"),
        "skills_path": str(tmp_path / "skills"),
        "mcp_servers": []
    }
    config_file.write_text(json.dumps(config_data))
    os.makedirs(config_data["skills_path"], exist_ok=True)

    service = AgentService(str(config_file))
    # Mock start components
    service.mcp_manager.start = AsyncMock()
    service.mcp_manager.stop = AsyncMock()

    # We don't want to actually start it fully as it blocks
    # But we can test stop()
    await service.stop()
    # verify it doesn't crash
