import asyncio
import signal
from .config import load_config
from .bus import MessageBus
from .persistence import Persistence
from .skills_loader import SkillsLoader
from .agent import AgentWrapper
from .mcp_manager import MCPManager
from google.adk.runners import Runner
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService


class AgentService:
    def __init__(self, config_path: str = "agent.json"):
        self.config = load_config(config_path)
        self.persistence = Persistence(self.config.db_path)
        self.bus = MessageBus(max_tasks=self.config.bus_max_tasks)
        self.skills_loader = SkillsLoader(self.config.skills_path)
        self.mcp_manager = MCPManager(self.config.mcp_servers)
        self.agent_wrapper = None
        self.runner = None
        self.stop_event = asyncio.Event()

    async def start(self):
        print("Starting ADK Agent Service...")

        # 1. Initialize Persistence (already done in __init__, but ensuring connection if needed)
        # Note: Persistence.get_history or other methods will handle connection.
        # Calling an internal method just to ensure it's ready if we wanted to be explicit:
        # await self.persistence._get_db()

        # 2. Start MCP Manager and Message Bus
        await self.mcp_manager.start()
        await self.bus.start()

        # 3. Create AgentWrapper
        self.agent_wrapper = await AgentWrapper.create(
            self.config, self.skills_loader, self.mcp_manager, self.persistence
        )

        # 4. Create ADK Runner
        self.runner = Runner(
            app_name="agent_service_app",
            agent=self.agent_wrapper.agent,
            session_service=self.persistence.session_service,
            memory_service=InMemoryMemoryService(),
            artifact_service=InMemoryArtifactService(),
        )

        # 5. Subscribe to commands
        await self.bus.subscribe_to_commands("agent_commands", self._handle_command)

        # 6. Start heartbeat loop
        asyncio.create_task(self.heartbeat_loop())

        # 7. Wait on stop_event
        print("Agent Service is running. Listening on 'agent_commands' channel.")
        await self.stop_event.wait()

    async def _handle_command(self, data: dict):
        source_id = data.get("source_id", "default")
        user_id = data.get("user_id", "default")
        content = data.get("content", "")

        print(f"Received command from {source_id}/{user_id}: {content}")

        if not self.agent_wrapper or not self.runner:
            print("Error: Agent not initialized")
            return

        response = await self.agent_wrapper.process_command(
            self.runner, source_id=source_id, user_id=user_id, content=content
        )

        # Publish response
        await self.bus.publish_response("agent_responses", response)
        print("Sent response to agent_responses")

    async def heartbeat_loop(self):
        interval = self.config.heartbeat_interval_minutes * 60
        while not self.stop_event.is_set():
            await asyncio.sleep(interval)
            if self.stop_event.is_set():
                break
            print("Heartbeat trigger")
            heartbeat_data = {
                "source_id": "system_heartbeat",
                "user_id": "system",
                "content": "Heartbeat trigger: Check for any pending tasks or status updates.",
            }
            await self._handle_command(heartbeat_data)

    async def stop(self):
        print("Stopping Agent Service...")
        self.stop_event.set()
        await self.bus.stop()
        if self.runner:
            await self.runner.close()
        await self.mcp_manager.stop()
        await self.persistence.close()


async def run_service():
    service = AgentService()

    # Handle signals
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(service.stop()))

    try:
        await service.start()
    except Exception as e:
        print(f"Service error: {e}")


def main():
    asyncio.run(run_service())


if __name__ == "__main__":
    main()
