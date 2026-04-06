import asyncio
import time
from julio.bus import MessageBus

async def main():
    # Large number of tasks to make O(N) more visible
    max_tasks = 1000
    bus = MessageBus(max_tasks=max_tasks)
    await bus.start()

    # Fill up the workers
    # We need to make the queue non-empty to trigger _maybe_spawn_worker in publish_response
    # or just call it directly.

    # Let's simulate many publish_response calls when queue is not empty
    # To keep queue non-empty, we can have a very slow subscriber or just put things in manually if we could,
    # but publish_response is better.

    async def slow_sub(msg):
        await asyncio.sleep(10) # Keep worker busy

    await bus.subscribe_to_commands("test", slow_sub)

    # Initially spawn all workers
    for i in range(max_tasks + 10):
        # We need to make sure queue stays non-empty to trigger _maybe_spawn_worker
        # but publish_response calls it BEFORE putting in the queue if it's already not empty.
        # Actually:
        # if not self._queue.empty():
        #     self._maybe_spawn_worker()
        # self._queue.put_nowait(...)

        # So we need at least one item in queue.
        await bus.publish_response("test", {"i": i})

    print(f"Workers spawned: {len(bus._workers)}")

    # Now measure time for many publish_response calls when workers are full
    iterations = 100000
    start = time.perf_counter()
    for i in range(iterations):
        # Trigger publish_response. It will call _maybe_spawn_worker because queue is not empty (slow_sub)
        await bus.publish_response("test", {"i": i})
    end = time.perf_counter()

    elapsed = end - start
    print(f"Time for {iterations} publish_calls with {max_tasks} workers: {elapsed:.4f}s")
    print(f"Average time per call: {elapsed/iterations*1e6:.4f}us")

    await bus.stop()

if __name__ == "__main__":
    asyncio.run(main())
