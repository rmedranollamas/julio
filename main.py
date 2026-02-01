import asyncio
import signal
import time
from config import load_config
from bus import MessageBus
from persistence import Persistence
from mcp_manager import MCPManager
from skills_loader import SkillsLoader
from agent import Agent

class AgentService:
    def __init__(self, config_path: str = "agent.json"):
        self.config = load_config(config_path)
        self.persistence = Persistence(self.config.db_path)
        self.bus = MessageBus(self.config.redis_url)
        self.mcp_manager = MCPManager(self.config.mcp_servers)
        self.skills_loader = SkillsLoader(self.config.skills_path)
        self.agent = Agent(self.config, self.persistence, self.mcp_manager, self.skills_loader)
        self.stop_event = asyncio.Event()

    async def start(self):
        print("Starting Agent Service...")

        # Start MCP servers
        await self.mcp_manager.start()

        # Subscribe to commands
        await self.bus.subscribe_to_commands("agent_commands", self._handle_command)

        # Start heartbeat loop
        asyncio.create_task(self.heartbeat_loop())

        print("Agent Service is running. Listening on 'agent_commands' channel.")
        await self.stop_event.wait()

    async def _handle_command(self, data: dict):
        source_id = data.get("source_id", "default")
        user_id = data.get("user_id", "default")
        content = data.get("content", "")

        print(f"Received command from {source_id}/{user_id}: {content}")

        response = await self.agent.process_command(source_id, user_id, content)

        # Publish response
        await self.bus.publish_response("agent_responses", response)
        print(f"Sent response to agent_responses")

    async def heartbeat_loop(self):
        interval = self.config.heartbeat_interval_minutes * 60
        while not self.stop_event.is_set():
            await asyncio.sleep(interval)
            if self.stop_event.is_set():
                break
            print("Heartbeat trigger")
            # In a real scenario, we might send a message to ourselves via the bus
            # or directly call the agent.
            heartbeat_data = {
                "source_id": "system",
                "user_id": "heartbeat",
                "content": "Heartbeat trigger: Check for any pending tasks or status updates."
            }
            await self._handle_command(heartbeat_data)

    async def stop(self):
        print("Stopping Agent Service...")
        self.stop_event.set()
        await self.mcp_manager.stop()
        await self.bus.stop()

async def main():
    service = AgentService()

    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(service.stop()))

    try:
        await service.start()
    except Exception as e:
        print(f"Service error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
