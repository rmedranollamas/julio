import asyncio
import logging
from typing import Callable, Dict, List, Awaitable

logger = logging.getLogger(__name__)


class MessageBus:
    """
    An in-memory message bus using asyncio.Queue.
    Replaces Redis for single-process environments.
    """

    def __init__(
        self, max_tasks: int = 1000, max_queue_size: int = 0, *args, **kwargs
    ):
        # We accept args/kwargs for compatibility with previous Redis-based init
        self._subscribers: Dict[str, List[Callable[[dict], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._max_tasks = max_tasks
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the worker pool."""
        self._workers = [
            asyncio.create_task(self._worker()) for _ in range(self._max_tasks)
        ]
        logger.info(f"Started {len(self._workers)} message bus workers.")

    async def _worker(self):
        """Worker task that processes messages from the queue."""
        while not self._stop_event.is_set():
            try:
                # Get the next callback/message pair from the queue
                callback, message = await self._queue.get()
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error in message bus subscriber: {e!r}")
                finally:
                    self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in message bus worker: {e!r}")

    async def publish_response(self, channel: str, message: dict):
        """Publishes a message to a specific channel."""
        if channel in self._subscribers:
            for callback in self._subscribers[channel]:
                try:
                    self._queue.put_nowait((callback, message))
                except asyncio.QueueFull:
                    logger.warning(
                        f"Message bus queue full, dropping message for channel: {channel}"
                    )

    async def subscribe_to_commands(
        self, channel: str, callback: Callable[[dict], Awaitable[None]]
    ):
        """Subscribes to a channel and registers a callback."""
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)

    async def stop(self):
        """Stops the message bus and its workers."""
        self._stop_event.set()
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Stopped message bus workers.")
