import asyncio
import time
import psutil
import os
from julio.bus import MessageBus

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

async def benchmark(max_tasks):
    print(f"Benchmarking with max_tasks={max_tasks}")

    initial_mem = get_memory_usage()

    start_time = time.time()
    bus = MessageBus(max_tasks=max_tasks)
    await bus.start()
    duration = time.time() - start_time

    post_start_mem = get_memory_usage()

    print(f"  Startup time: {duration:.4f}s")
    print(f"  Memory increase: {post_start_mem - initial_mem:.4f} MB")

    # Do some work
    results = []
    async def slow_sub(msg):
        await asyncio.sleep(0.01)
        results.append(msg)

    await bus.subscribe_to_commands("test", slow_sub)

    work_start = time.time()
    num_messages = 100
    for i in range(num_messages):
        await bus.publish_response("test", {"i": i})

    # Wait for all messages to be processed
    while len(results) < num_messages:
        await asyncio.sleep(0.01)

    work_duration = time.time() - work_start
    print(f"  Work duration (100 msgs): {work_duration:.4f}s")

    await bus.stop()
    final_mem = get_memory_usage()
    print(f"  Memory after stop: {final_mem:.4f} MB")
    print("-" * 30)

async def main():
    # Warm up
    bus = MessageBus(max_tasks=1)
    await bus.start()
    await bus.stop()

    await benchmark(10)
    await benchmark(100)
    await benchmark(1000)
    await benchmark(5000)

if __name__ == "__main__":
    asyncio.run(main())
