import asyncio
import logging
import collections
from typing import Callable, Dict, List, Awaitable, Set

logger = logging.getLogger(__name__)


class MessageBus:
    """
    An in-memory message bus using asyncio.Queue.
    Replaces Redis for single-process environments.
    """

    def __init__(self, max_tasks: int = 1000, *args, **kwargs):
        # We accept args/kwargs for compatibility with previous Redis-based init
        self._subscribers: Dict[str, List[Callable[[dict], Awaitable[None]]]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._tasks: Set[asyncio.Task] = set()
        self._pending = collections.deque()
        self._max_tasks = max_tasks
        self.stop_event = asyncio.Event()
        self._shutting_down = False

    def _handle_task_completion(self, task: asyncio.Task) -> None:
        """Done callback to handle task completion and exceptions."""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in message bus subscriber task: {e!r}")
        finally:
            self._tasks.discard(task)
            # When a task completes, check if we can start any pending work
            if not self._shutting_down:
                self._process_pending()

    def _process_pending(self) -> None:
        """Starts pending subscriber callbacks up to the max_tasks limit."""
        while self._pending and len(self._tasks) < self._max_tasks:
            callback, message = self._pending.popleft()
            task = asyncio.create_task(callback(message))
            self._tasks.add(task)
            task.add_done_callback(self._handle_task_completion)

    async def publish_response(self, channel: str, message: dict):
        """Publishes a message to a specific channel."""
        if self._shutting_down:
            return

        if channel in self._subscribers:
            # Add each subscriber callback to the pending queue
            for callback in self._subscribers[channel]:
                self._pending.append((callback, message))

            # Try to process pending work immediately
            self._process_pending()

    async def subscribe_to_commands(
        self, channel: str, callback: Callable[[dict], Awaitable[None]]
    ):
        """Subscribes to a channel and registers a callback."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    async def stop(self):
        """Stops the message bus."""
        self._shutting_down = True
        self.stop_event.set()

        # Clear any pending work that hasn't started
        self._pending.clear()

        # In-memory bus doesn't have persistent connections to close
        if self._tasks:
            # Create a copy to avoid "Set size changed during iteration" if tasks finish
            tasks = list(self._tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
