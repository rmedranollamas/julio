import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from agent import AgentWrapper, AgentConfig

@pytest.mark.asyncio
async def test_agent_wrapper():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")

    wrapper = AgentWrapper(config, skills_loader)
    await wrapper.initialize()
    assert wrapper.agent.name == "agent_service"
    assert "Skills" in wrapper.agent.instruction

@pytest.mark.asyncio
async def test_agent_run():
    config = AgentConfig(gemini_api_key="key")
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    wrapper = AgentWrapper(config, skills_loader)
    await wrapper.initialize()

    mock_runner = MagicMock()
    from google.adk.events import Event
    from google.genai import types

    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[types.Part(text="ADK Response [NEEDS_INPUT]")])
    )

    def mock_gen(*args, **kwargs):
        async def gen():
            yield event
        return gen()

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.run_with_runner(mock_runner, "user1", "session1", "hello")
    assert result["content"] == "ADK Response [NEEDS_INPUT]"
    assert result["needs_input"] is True
