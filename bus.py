import redis.asyncio as redis
import json
import asyncio
from typing import Callable, Optional, Awaitable

class MessageBus:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pubsub = self.redis.pubsub()
        self.stop_event = asyncio.Event()
        self.listen_task = None

    async def publish_response(self, channel: str, message: dict):
        await self.redis.publish(channel, json.dumps(message))

    async def subscribe_to_commands(self, channel: str, callback: Callable[[dict], Awaitable[None]]):
        await self.pubsub.subscribe(channel)

        async def listen():
            while not self.stop_event.is_set():
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message['type'] == 'message':
                        await self._handle_message(message, callback)
                except Exception as e:
                    if not self.stop_event.is_set():
                        print(f"Error in message bus loop: {e}")
                await asyncio.sleep(0.01)

        self.listen_task = asyncio.create_task(listen())

    async def _handle_message(self, message: dict, callback: Callable[[dict], Awaitable[None]]):
        try:
            data = json.loads(message['data'])
            await callback(data)
        except json.JSONDecodeError:
            print(f"Failed to decode message data: {message['data']}")

    async def stop(self):
        self.stop_event.set()
        if self.listen_task:
            await self.listen_task
        await self.pubsub.close()
        await self.redis.close()
