import pytest
import asyncio
import logging
from julio.bus import MessageBus

@pytest.mark.asyncio
async def test_bus_bounded_queue(caplog):
    # Set a very small queue size
    bus = MessageBus(max_tasks=1, max_queue_size=2)
    await bus.start()

    worker_picked_up_event = asyncio.Event()
    results = []
    async def slow_sub(msg):
        worker_picked_up_event.set()
        await asyncio.sleep(0.1)
        results.append(msg)

    await bus.subscribe_to_commands("test", slow_sub)

    # First message: picked up by worker immediately (but worker waits 0.1s)
    # The queue is now empty, but worker is busy.
    await bus.publish_response("test", {"id": 1})

    # Wait for the worker to signal it has picked up the message
    await worker_picked_up_event.wait()

    # Second message: goes to queue (size 1/2)
    await bus.publish_response("test", {"id": 2})
    # Third message: goes to queue (size 2/2)
    await bus.publish_response("test", {"id": 3})

    # Fourth message: should fail and log warning
    with caplog.at_level(logging.WARNING):
        await bus.publish_response("test", {"id": 4})

    assert "Message bus queue full (2), dropping message for channel: test" in caplog.text

    # Wait for all to finish
    await asyncio.sleep(0.5)

    # Only 3 messages should have been processed
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2
    assert results[2]["id"] == 3

    await bus.stop()
