import asyncio
import logging
import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from julio.bus import MessageBus

class TestMessageBus(unittest.IsolatedAsyncioTestCase):
    async def test_bus_multiple_subscribers(self):
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
        for _ in range(100):
            if len(results) == 2:
                break
            await asyncio.sleep(0.01)

        self.assertIn("sub1:hi", results)
        self.assertIn("sub2:hi", results)
        await bus.stop()

    async def test_bus_subscriber_error(self):
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

    async def test_bus_stop_cleanup(self):
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

        await bus.stop()
        self.assertFalse(finish_event.is_set())

    async def test_bus_dynamic_spawning(self):
        bus = MessageBus(max_tasks=10)
        await bus.start()

        # Initially should have 1 worker
        self.assertEqual(len(bus._workers), 1)

        results = []
        async def slow_sub(msg):
            await asyncio.sleep(0.1)
            results.append(msg)

        await bus.subscribe_to_commands("test", slow_sub)

        # Publish many messages to force queue buildup and dynamic spawning
        for i in range(5):
            await bus.publish_response("test", {"i": i})

        # Should have spawned more workers
        self.assertGreater(len(bus._workers), 1)

        await bus.stop()

if __name__ == "__main__":
    unittest.main()
