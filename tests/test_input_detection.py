import pytest
from unittest.mock import MagicMock, AsyncMock
from julio.agent import AgentWrapper
from julio.config import AgentConfig
from google.adk.events import Event
from google.genai import types


@pytest.mark.asyncio
async def test_input_detection_tool_call():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []
    persistence = MagicMock()
    wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)

    mock_runner = MagicMock()

    # Simulate a tool call event
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        name="request_user_input",
                        args={"question": "What is your name?"},
                    )
                )
            ]
        ),
    )

    def mock_gen(*args, **kwargs):
        async def gen():
            yield event

        return gen()

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.process_command(mock_runner, "session1", "user1", "hello")
    assert "What is your name?" in result["content"]
    assert result["needs_input"] is True


@pytest.mark.asyncio
async def test_input_detection_keyword():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []
    persistence = MagicMock()
    wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)

    mock_runner = MagicMock()

    # Simulate a keyword response
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(
            parts=[types.Part(text="I need more info [NEEDS_INPUT]")]
        ),
    )

    def mock_gen(*args, **kwargs):
        async def gen():
            yield event

        return gen()

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.process_command(mock_runner, "session1", "user1", "hello")
    assert "I need more info [NEEDS_INPUT]" in result["content"]
    assert result["needs_input"] is True


@pytest.mark.asyncio
async def test_input_detection_none():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills = AsyncMock(return_value="Skills")
    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []
    persistence = MagicMock()
    wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)

    mock_runner = MagicMock()

    # Simulate a normal response
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[types.Part(text="Everything is fine.")]),
    )

    def mock_gen(*args, **kwargs):
        async def gen():
            yield event

        return gen()

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.process_command(mock_runner, "session1", "user1", "hello")
    assert result["content"] == "Everything is fine."
    assert result["needs_input"] is False
