import asyncio
import json
import os
import fakeredis.aioredis as fakeredis
from unittest.mock import AsyncMock, patch, MagicMock
from main import AgentService
from config import AgentConfig

async def run_demo():
    print("--- Starting ADK Agent Service Demo ---")

    # 1. Setup Mock Config
    config = AgentConfig(
        gemini_api_key="mock_key",
        redis_url="redis://localhost",
        heartbeat_interval_minutes=0.1 # 6 seconds
    )

    # 2. Setup Mocks
    with patch('main.load_config', return_value=config), \
         patch('bus.redis.from_url') as mock_redis_from_url, \
         patch('google.adk.runners.Runner.run_async') as mock_run_async:

        # Fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        mock_redis_from_url.return_value = fake_redis

        # Mock ADK Runner output
        async def mock_runner_gen(*args, **kwargs):
            from google.adk.events import Event
            from google.genai import types
            event = Event(
                invocation_id="test",
                author="agent_service",
                content=types.Content(parts=[types.Part(text="I am the ADK agent. [NEEDS_INPUT]")])
            )
            yield event

        mock_run_async.side_effect = mock_runner_gen

        # 3. Initialize Service
        service = AgentService()

        # Start service in background
        service_task = asyncio.create_task(service.start())
        await asyncio.sleep(0.5) # Wait for service to start

        # 4. Simulate a Client
        client_redis = fake_redis
        pubsub = client_redis.pubsub()
        await pubsub.subscribe("agent_responses")

        print("Client: Sending command 'hello'...")
        await client_redis.publish("agent_commands", json.dumps({
            "source_id": "demo_session_1",
            "user_id": "demo_user",
            "content": "hello"
        }))

        # 5. Listen for Response
        print("Client: Waiting for response...")
        for _ in range(10): # Timeout loop
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if msg:
                data = json.loads(msg['data'])
                print(f"Client: Received response from agent!")
                print(f"Agent says: {data['content']}")
                print(f"Needs input: {data['needs_input']}")
                break
            await asyncio.sleep(0.1)

        # 6. Cleanup
        print("Stopping demo...")
        await service.stop()
        await service_task

if __name__ == "__main__":
    asyncio.run(run_demo())
