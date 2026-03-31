import asyncio
import time
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from julio.bus import MessageBus

def get_process_memory():
    try:
        with open('/proc/self/status') as f:
            for line in f:
                if line.startswith('VmRSS:'):
                    return int(line.split()[1]) / 1024
    except:
        return 0

async def benchmark(max_tasks):
    print(f"Benchmarking with max_tasks={max_tasks}")

    initial_mem = get_process_memory()

    start_time = time.time()
    bus = MessageBus(max_tasks=max_tasks)
    await bus.start()
    duration = time.time() - start_time

    post_start_mem = get_process_memory()
    num_initial_workers = len(bus._workers)

    print(f"  Startup time: {duration:.4f}s")
    print(f"  Initial workers: {num_initial_workers}")
    print(f"  Memory increase at startup: {post_start_mem - initial_mem:.4f} MB")

    results = []
    async def slow_sub(msg):
        await asyncio.sleep(0.001)
        results.append(msg)

    await bus.subscribe_to_commands("test", slow_sub)

    work_start = time.time()
    num_messages = 100
    for i in range(num_messages):
        await bus.publish_response("test", {"i": i})

    while len(results) < num_messages:
        await asyncio.sleep(0.001)

    work_duration = time.time() - work_start
    final_workers = len(bus._workers)
    print(f"  Work duration (100 msgs): {work_duration:.4f}s")
    print(f"  Final workers: {final_workers}")

    await bus.stop()
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
