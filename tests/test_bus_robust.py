import pytest
import asyncio
from julio.bus import MessageBus

@pytest.mark.asyncio
async def test_bus_multiple_subscribers():
    bus = MessageBus()
    results = []

    async def sub1(msg):
        results.append(f"sub1:{msg['val']}")

    async def sub2(msg):
        results.append(f"sub2:{msg['val']}")

    await bus.subscribe_to_commands("test", sub1)
    await bus.subscribe_to_commands("test", sub2)

    await bus.publish_response("test", {"val": "hi"})
    await asyncio.sleep(0.05)

    assert "sub1:hi" in results
    assert "sub2:hi" in results
    await bus.stop()

@pytest.mark.asyncio
async def test_bus_subscriber_error():
    bus = MessageBus()

    async def failing_sub(msg):
        raise ValueError("Boom")

    async def working_sub(msg):
        await asyncio.sleep(0.01)

    await bus.subscribe_to_commands("test", failing_sub)
    await bus.subscribe_to_commands("test", working_sub)

    # This should not crash the publisher
    await bus.publish_response("test", {"val": "hi"})
    await asyncio.sleep(0.05)

    # Check that tasks are cleaned up even if they failed
    assert len(bus._tasks) == 0
    await bus.stop()

@pytest.mark.asyncio
async def test_bus_stop_cleanup():
    bus = MessageBus()

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

    await start_event.wait()
    assert len(bus._tasks) == 1

    await bus.stop()
    assert len(bus._tasks) == 0
    assert not finish_event.is_set()
