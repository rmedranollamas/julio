import asyncio
from typing import Callable, Dict, List, Awaitable, Set


class MessageBus:
    """
    An in-memory message bus using asyncio.Queue.
    Replaces Redis for single-process environments.
    """

    def __init__(self, *args, **kwargs):
        # We accept args/kwargs for compatibility with previous Redis-based init
        self._subscribers: Dict[str, List[Callable[[dict], Awaitable[None]]]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._tasks: Set[asyncio.Task] = set()
        self.stop_event = asyncio.Event()

    async def publish_response(self, channel: str, message: dict):
        """Publishes a message to a specific channel."""
        if channel in self._subscribers:
            # Create a task for each subscriber to handle the message
            for callback in self._subscribers[channel]:
                task = asyncio.create_task(callback(message))
                self._tasks.add(task)
                task.add_done_callback(self._tasks.discard)

    async def subscribe_to_commands(
        self, channel: str, callback: Callable[[dict], Awaitable[None]]
    ):
        """Subscribes to a channel and registers a callback."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    async def stop(self):
        """Stops the message bus."""
        self.stop_event.set()
        # In-memory bus doesn't have persistent connections to close
        if self._tasks:
            # Create a copy to avoid "Set size changed during iteration" if tasks finish
            tasks = list(self._tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
