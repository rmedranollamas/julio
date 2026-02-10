import asyncio
import time
import os
from unittest.mock import AsyncMock, MagicMock
from julio.agent import AgentWrapper
from julio.persistence import Persistence
from julio.config import AgentConfig

async def benchmark():
    # Setup
    db_path = "benchmark.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    config = AgentConfig(
        gemini_api_key="fake_key",
        db_path=db_path,
        mcp_servers=[],
        skills_path="skills",
        heartbeat_interval_minutes=1.0,
        shell_command_timeout=30
    )

    persistence = Persistence(db_path)
    # Ensure DB is created and has some data
    db = await persistence._get_db()
    await db.execute("CREATE TABLE IF NOT EXISTS events (session_id TEXT, user_id TEXT, event_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    for i in range(10):
        await db.execute("INSERT INTO events (session_id, user_id, event_data) VALUES (?, ?, ?)",
                         ("session1", "user1", '{"event": "data"}'))
    await db.commit()

    skills_loader = AsyncMock()
    skills_loader.load_skills.return_value = "Some skills"

    mcp_manager = MagicMock()
    mcp_manager.get_toolsets.return_value = []

    # We need to mock LlmAgent because it tries to call Google GenAI API
    with MagicMock() as mock_llm_agent:
        AgentWrapper._create_agent = AsyncMock(return_value=mock_llm_agent)
        agent_wrapper = await AgentWrapper.create(config, skills_loader, mcp_manager, persistence)

    runner = AsyncMock()
    # Mock runner.run_async to be an async generator
    async def empty_gen(*args, **kwargs):
        if False: yield None
    runner.run_async = empty_gen

    # Measure
    start_time = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        await agent_wrapper.process_command(runner, "session1", "user1", "hello")
    end_time = time.perf_counter()

    print(f"Total time for {iterations} iterations: {end_time - start_time:.4f}s")
    print(f"Average time per iteration: {(end_time - start_time) / iterations:.6f}s")

    await persistence.close()
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(benchmark())
