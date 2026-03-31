import asyncio
import logging
from typing import Callable, Dict, List, Awaitable, Set

logger = logging.getLogger(__name__)


class MessageBus:
    """
    An in-memory message bus using asyncio.Queue.
    Replaces Redis for single-process environments.
    """

    def __init__(self, max_tasks: int = 50, max_queue_size: int = 0, *args, **kwargs):
        # We accept args/kwargs for compatibility with previous Redis-based init
        self._subscribers: Dict[str, Set[Callable[[dict], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size)
        self._max_tasks = max_tasks
        self._workers: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the worker pool with an initial worker."""
        self._maybe_spawn_worker()
        logger.info("Started message bus.")

    def _maybe_spawn_worker(self):
        """Spawns a new worker task if we haven't reached the limit."""
        # Clean up finished tasks to allow replacement and restartability
        self._workers = [t for t in self._workers if not t.done()]
        if len(self._workers) < self._max_tasks:
            worker = asyncio.create_task(self._worker())
            self._workers.append(worker)
            return True
        return False

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
            # If the queue is not empty, it might be a sign we need more workers
            if not self._queue.empty():
                self._maybe_spawn_worker()

            for callback in self._subscribers[channel]:
                try:
                    self._queue.put_nowait((callback, message))
                except asyncio.QueueFull:
                    logger.warning(
                        f"Message bus queue full ({self._queue.maxsize}), dropping message for channel: {channel}"
                    )

    async def subscribe_to_commands(
        self, channel: str, callback: Callable[[dict], Awaitable[None]]
    ):
        """Subscribes to a channel and registers a callback."""
        if channel not in self._subscribers:
            self._subscribers[channel] = set()
        self._subscribers[channel].add(callback)

    async def stop(self):
        """Stops the message bus and its workers."""
        self._stop_event.set()
        for worker in self._workers:
            worker.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Stopped message bus workers.")
