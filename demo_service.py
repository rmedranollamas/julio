import asyncio
import json
import fakeredis.aioredis as fakeredis
from unittest.mock import AsyncMock, patch, MagicMock
from main import AgentService
from config import AgentConfig

async def run_demo():
    print("--- Starting Agent Service Demo ---")

    # 1. Setup Mock Config
    config = AgentConfig(
        gemini_api_key="mock_key",
        redis_url="redis://localhost",
        heartbeat_interval_minutes=0.1 # 6 seconds
    )

    # 2. Setup Mocks
    with patch('main.load_config', return_value=config), \
         patch('bus.redis.from_url') as mock_redis_from_url, \
         patch('google.generativeai.GenerativeModel') as mock_model_class:

        # Fake Redis
        fake_redis = fakeredis.FakeRedis(decode_responses=True)
        mock_redis_from_url.return_value = fake_redis

        # Mock Gemini
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        mock_chat = AsyncMock()
        mock_model.start_chat.return_value = mock_chat

        # Define how the mock agent responds
        async def mock_send_message(content):
            resp = MagicMock()
            if "files" in content:
                resp.text = "I see several files here: agent.py, main.py, etc. [NEEDS_INPUT]"
            else:
                resp.text = f"I received your message: '{content}'. How can I help? [NEEDS_INPUT]"
            return resp

        mock_chat.send_message_async.side_effect = mock_send_message

        # 3. Initialize Service
        service = AgentService()

        # Start service in background
        service_task = asyncio.create_task(service.start())
        await asyncio.sleep(0.5) # Wait for service to start

        # 4. Simulate a Client
        client_redis = fake_redis
        pubsub = client_redis.pubsub()
        await pubsub.subscribe("agent_responses")

        print("Client: Sending command 'list my files'...")
        await client_redis.publish("agent_commands", json.dumps({
            "source_id": "demo_chat",
            "user_id": "jules_user",
            "content": "Please list my files"
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

        # 6. Test Heartbeat (it should trigger after ~0.6 seconds due to interval=0.01)
        print("Waiting for heartbeat...")
        await asyncio.sleep(1.0)

        # 7. Cleanup
        print("Stopping demo...")
        await service.stop()
        await service_task

if __name__ == "__main__":
    asyncio.run(run_demo())
