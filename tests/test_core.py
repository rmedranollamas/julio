import pytest
import json
import asyncio
from julio.persistence import Persistence
from julio.config import load_config
from julio.bus import MessageBus
from julio.tools_internal import run_shell_command, list_files, read_file, write_file


# Persistence Tests
@pytest.mark.asyncio
async def test_persistence(tmp_path):
    db_path = str(tmp_path / "test.db")
    p = Persistence(db_path)
    # Testing SqliteSessionService via ADK is better done in integrated tests,
    # but let's just check it initializes.
    assert p.session_service is not None


# Config Tests
def test_config(tmp_path):
    cfg_file = tmp_path / "agent.json"
    cfg_data = {"gemini_api_key": "test_key", "mcp_servers": []}
    cfg_file.write_text(json.dumps(cfg_data))
    config = load_config(str(cfg_file))
    assert config.gemini_api_key == "test_key"
    assert config.heartbeat_interval_minutes == 5.0


# Bus Tests
@pytest.mark.asyncio
async def test_bus():
    bus = MessageBus()

    received = []

    async def callback(msg):
        received.append(msg)

    await bus.subscribe_to_commands("cmd", callback)
    await bus.publish_response("cmd", {"data": "test"})
    # Since it's in-memory and uses asyncio.create_task, we need a tiny yield
    await asyncio.sleep(0.01)
    assert len(received) == 1
    assert received[0]["data"] == "test"
    await bus.stop()


# Internal Tools Tests
@pytest.mark.asyncio
async def test_tools_internal(tmp_path):
    test_file = tmp_path / "test.txt"
    assert "Successfully wrote" in await write_file(str(test_file), "hello")
    assert await read_file(str(test_file)) == "hello"
    assert str(test_file.name) in await list_files(str(tmp_path))
    assert "STDOUT:\nechoed\n" in await run_shell_command("echo echoed")
