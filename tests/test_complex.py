import pytest
from unittest.mock import MagicMock, AsyncMock
from agent import AgentWrapper, AgentConfig


@pytest.mark.asyncio
async def test_agent_wrapper():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []
    persistence = MagicMock()

    wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)
    assert wrapper.agent.name == "agent_service"
    assert "Skills" in wrapper.agent.instruction


@pytest.mark.asyncio
async def test_agent_run():
    config = AgentConfig(gemini_api_key="key")
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []
    persistence = MagicMock()
    wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)

    mock_runner = MagicMock()
    from google.adk.events import Event
    from google.genai import types

    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[types.Part(text="ADK Response [NEEDS_INPUT]")]),
    )

    def mock_gen(*args, **kwargs):
        async def gen():
            yield event

        return gen()

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.run_with_runner(mock_runner, "user1", "session1", "hello")
    assert result["content"] == "ADK Response [NEEDS_INPUT]"
    assert result["needs_input"] is True
