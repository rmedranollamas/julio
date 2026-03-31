import asyncio
import time
import os
from typing import Callable, Dict, List, Awaitable, Set

# Mock logger
class MockLogger:
    def info(self, msg): pass
    def error(self, msg): pass
    def warning(self, msg): pass
logger = MockLogger()

# Simplified MessageBus for benchmarking
class MessageBus:
    def __init__(self, max_tasks: int = 1000, max_queue_size: int = 0):
        self._subscribers: Dict[str, Set[Callable[[dict], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._max_tasks = max_tasks
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self):
        self._workers = [
            asyncio.create_task(self._worker()) for _ in range(self._max_tasks)
        ]

    async def _worker(self):
        while not self._stop_event.is_set():
            try:
                callback, message = await self._queue.get()
                try:
                    await callback(message)
                except Exception:
                    pass
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                pass

    async def publish_response(self, channel: str, message: dict):
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                try:
                    self._queue.put_nowait((callback, message))
                except asyncio.QueueFull:
                    pass

    async def subscribe_to_commands(self, channel: str, callback: Callable[[dict], Awaitable[None]]):
        if channel not in self._subscribers:
            self._subscribers[channel] = set()
        self._subscribers[channel].add(callback)

    async def stop(self):
        self._stop_event.set()
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)

def get_process_memory():
    # Fallback if psutil is not available
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        # Try reading from /proc/self/status
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

    print(f"  Startup time: {duration:.4f}s")
    print(f"  Memory increase: {post_start_mem - initial_mem:.4f} MB")

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
    print(f"  Work duration (100 msgs): {work_duration:.4f}s")

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
