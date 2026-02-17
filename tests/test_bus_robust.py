import pytest
import asyncio
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
