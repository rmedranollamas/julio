import json
import asyncio
from bus import MessageBus
import fakeredis.aioredis as fakeredis

async def test_bus_async():
    # Patch MessageBus to use fakeredis for testing
    bus = MessageBus("redis://localhost:6379")
    # Replace the redis client with fakeredis
    bus.redis = fakeredis.FakeRedis(decode_responses=True)
    bus.pubsub = bus.redis.pubsub()

    received_messages = []
    async def callback(msg):
        received_messages.append(msg)

    await bus.subscribe_to_commands("test_commands", callback)

    await asyncio.sleep(0.1)
    await bus.publish_response("test_commands", {"text": "hello agent"})

    await asyncio.sleep(0.5)

    if len(received_messages) > 0:
        print(f"Received: {received_messages[0]}")
        if received_messages[0]["text"] == "hello agent":
            print("Message bus test PASSED")
        else:
            print("Message bus test FAILED (content mismatch)")
    else:
        print("Message bus test FAILED (no message received)")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(test_bus_async())
