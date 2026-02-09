import asyncio
import logging
from typing import Callable, Dict, List, Awaitable, Set

logger = logging.getLogger(__name__)


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

    async def publish_response(self, channel: str, message: dict):
        """Publishes a message to a specific channel."""
        if self._shutting_down:
            return

        if channel in self._subscribers:
            # Create a task for each subscriber to handle the message
            for callback in self._subscribers[channel]:
                task = asyncio.create_task(callback(message))
                self._tasks.add(task)
                task.add_done_callback(self._handle_task_completion)

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
        # In-memory bus doesn't have persistent connections to close
        if self._tasks:
            # Create a copy to avoid "Set size changed during iteration" if tasks finish
            tasks = list(self._tasks)
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
