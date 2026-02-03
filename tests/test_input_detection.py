import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from agent import AgentWrapper, AgentConfig
from google.adk.events import Event
from google.genai import types

@pytest.mark.asyncio
async def test_input_detection_tool_call():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills.return_value = "Skills"
    wrapper = AgentWrapper(config, skills_loader)

    mock_runner = MagicMock()

    # Simulate a tool call event
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[
            types.Part(function_call=types.FunctionCall(
                name="request_user_input",
                args={"question": "What is your name?"}
            ))
        ])
    )

    async def mock_gen(*args, **kwargs):
        yield event

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.run_with_runner(mock_runner, "user1", "session1", "hello")
    assert "What is your name?" in result["content"]
    assert result["needs_input"] is True

@pytest.mark.asyncio
async def test_input_detection_keyword():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills.return_value = "Skills"
    wrapper = AgentWrapper(config, skills_loader)

    mock_runner = MagicMock()

    # Simulate a keyword response
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[
            types.Part(text="I need more info [NEEDS_INPUT]")
        ])
    )

    async def mock_gen(*args, **kwargs):
        yield event

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.run_with_runner(mock_runner, "user1", "session1", "hello")
    assert "I need more info [NEEDS_INPUT]" in result["content"]
    assert result["needs_input"] is True

@pytest.mark.asyncio
async def test_input_detection_none():
    config = AgentConfig(gemini_api_key="key", mcp_servers=[])
    skills_loader = MagicMock()
    skills_loader.load_skills.return_value = "Skills"
    wrapper = AgentWrapper(config, skills_loader)

    mock_runner = MagicMock()

    # Simulate a normal response
    event = Event(
        invocation_id="test",
        author="agent_service",
        content=types.Content(parts=[
            types.Part(text="Everything is fine.")
        ])
    )

    async def mock_gen(*args, **kwargs):
        yield event

    mock_runner.run_async.side_effect = mock_gen

    result = await wrapper.run_with_runner(mock_runner, "user1", "session1", "hello")
    assert result["content"] == "Everything is fine."
    assert result["needs_input"] is False
