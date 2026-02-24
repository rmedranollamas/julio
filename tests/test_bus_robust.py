import asyncio
import logging

import pytest

from julio.bus import MessageBus


@pytest.mark.asyncio
async def test_bus_multiple_subscribers():
    bus = MessageBus(max_tasks=2)
    await bus.start()
    results = []

    async def sub1(msg):
        results.append(f"sub1:{msg['val']}")

    async def sub2(msg):
        results.append(f"sub2:{msg['val']}")

    await bus.subscribe_to_commands("test", sub1)
    await bus.subscribe_to_commands("test", sub2)

    await bus.publish_response("test", {"val": "hi"})

    # Wait for workers to process
    for _ in range(10):
        if len(results) == 2:
            break
        await asyncio.sleep(0.01)

    assert "sub1:hi" in results
    assert "sub2:hi" in results
    await bus.stop()


@pytest.mark.asyncio
async def test_bus_subscriber_error():
    bus = MessageBus(max_tasks=2)
    await bus.start()

    async def failing_sub(msg):
        raise ValueError("Boom")

    async def working_sub(msg):
        await asyncio.sleep(0.01)

    await bus.subscribe_to_commands("test", failing_sub)
    await bus.subscribe_to_commands("test", working_sub)

    # This should not crash the publisher or other workers
    await bus.publish_response("test", {"val": "hi"})
    await asyncio.sleep(0.05)

    await bus.stop()


@pytest.mark.asyncio
async def test_bus_stop_cleanup():
    bus = MessageBus(max_tasks=1)
    await bus.start()

    start_event = asyncio.Event()
    finish_event = asyncio.Event()

    async def long_sub(msg):
        start_event.set()
        try:
            await asyncio.sleep(1)
            finish_event.set()
        except asyncio.CancelledError:
            # Expected on stop
            pass

    await bus.subscribe_to_commands("test", long_sub)
    await bus.publish_response("test", {"val": "hi"})

    await asyncio.wait_for(start_event.wait(), timeout=1.0)

    # In the new implementation, workers are always present.
    # We just want to make sure they stop gracefully.
    await bus.stop()
    assert not finish_event.is_set()


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

    assert (
        "Message bus queue full (2), dropping message for channel: test" in caplog.text
    )

    # Wait for all to finish
    await asyncio.sleep(0.5)

    # Only 3 messages should have been processed
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[1]["id"] == 2
    assert results[2]["id"] == 3

    await bus.stop()
