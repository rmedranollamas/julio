import asyncio
from unittest.mock import patch, AsyncMock
from julio.main import AgentService
from julio.config import AgentConfig


async def run_demo():
    print("--- Starting ADK Agent Service Demo (In-Memory) ---")

    # 1. Setup Mock Config
    config = AgentConfig(
        gemini_api_key="mock_key",
        heartbeat_interval_minutes=0.1,  # 6 seconds
    )

    # 2. Setup Mocks
    with (
        patch("julio.main.load_config", return_value=config),
        patch("google.adk.runners.Runner.run_async") as mock_run_async,
        patch(
            "julio.persistence.Persistence.get_history", new_callable=AsyncMock
        ) as mock_get_history,
    ):
        mock_get_history.return_value = []

        # Mock ADK Runner output
        async def mock_runner_gen(*args, **kwargs):
            from google.adk.events import Event
            from google.genai import types

            event = Event(
                invocation_id="test",
                author="agent_service",
                content=types.Content(
                    parts=[types.Part(text="I am the ADK agent. [NEEDS_INPUT]")]
                ),
            )
            yield event

        mock_run_async.side_effect = mock_runner_gen

        # 3. Initialize Service
        service = AgentService()

        # Start service in background
        service_task = asyncio.create_task(service.start())
        await asyncio.sleep(0.5)  # Wait for service to start

        # 4. Simulate a Client using the bus directly
        received_response = asyncio.Event()
        response_data = {}

        async def on_response(data):
            nonlocal response_data
            response_data = data
            received_response.set()

        await service.bus.subscribe_to_commands("agent_responses", on_response)

        print("Client: Sending command 'hello'...")
        await service.bus.publish_response(
            "agent_commands",
            {"source_id": "demo_session_1", "user_id": "demo_user", "content": "hello"},
        )

        # 5. Listen for Response
        print("Client: Waiting for response...")
        try:
            await asyncio.wait_for(received_response.wait(), timeout=5.0)
            print("Client: Received response from agent!")
            print(f"Agent says: {response_data['content']}")
            print(f"Needs input: {response_data['needs_input']}")
        except asyncio.TimeoutError:
            print("Client: Timeout waiting for response.")

        # 6. Cleanup
        print("Stopping demo...")
        await service.stop()
        await service_task


if __name__ == "__main__":
    asyncio.run(run_demo())
