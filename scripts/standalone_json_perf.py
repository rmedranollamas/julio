import asyncio
import json
import time

def blocking_json_loads(data):
    # Simulate multiple JSON loads
    return [json.loads(d) for d in data]

async def heartbeat(stop_event):
    latencies = []
    while not stop_event.is_set():
        start = time.perf_counter()
        await asyncio.sleep(0.001)
        latencies.append(time.perf_counter() - start - 0.001)
    return latencies

async def run_demo():
    # Create 50MB of JSON data (50 x 1MB)
    print("Generating data...")
    item = json.dumps({"data": "x" * 1000000})
    data = [item] * 50

    # Establish Baseline (Sync)
    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(heartbeat(stop_event))
    await asyncio.sleep(0.1)

    print("Running synchronous JSON loads...")
    start = time.perf_counter()
    blocking_json_loads(data)
    sync_duration = time.perf_counter() - start

    stop_event.set()
    sync_latencies = await hb_task

    print(f"Sync duration: {sync_duration:.4f}s")
    print(f"Max loop lag (sync): {max(sync_latencies)*1000:.2f}ms")

    # Measure Optimized (Async Offloaded)
    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(heartbeat(stop_event))
    await asyncio.sleep(0.1)

    print("\nRunning asynchronous JSON loads (offloaded)...")
    start = time.perf_counter()
    await asyncio.to_thread(blocking_json_loads, data)
    async_duration = time.perf_counter() - start

    stop_event.set()
    async_latencies = await hb_task

    print(f"Async duration: {async_duration:.4f}s")
    print(f"Max loop lag (async): {max(async_latencies)*1000:.2f}ms")

if __name__ == "__main__":
    asyncio.run(run_demo())
