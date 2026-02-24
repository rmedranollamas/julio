import asyncio
import os
import psutil
import time
from julio.bus import MessageBus

async def main():
    # Set a small queue size for testing
    bus = MessageBus(max_tasks=1, max_queue_size=100)
    await bus.start()

    process = psutil.Process(os.getpid())

    async def slow_subscriber(msg):
        await asyncio.sleep(0.1)

    await bus.subscribe_to_commands("bench", slow_subscriber)

    print(f"Initial memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

    num_messages = 1000
    for i in range(num_messages):
        await bus.publish_response("bench", {"data": "x" * 1000})
        if i % 100 == 0:
             print(f"Published {i} messages... Queue size: {bus._queue.qsize()}... Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

    print(f"Finished publishing. Final Queue size: {bus._queue.qsize()}")
    print(f"Final memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
