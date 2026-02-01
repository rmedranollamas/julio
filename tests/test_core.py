import pytest
import os
import json
import asyncio
import sqlite3
import fakeredis.aioredis as fakeredis
from persistence import Persistence
from config import load_config, AgentConfig
from bus import MessageBus
from tools_internal import run_shell_command, list_files, read_file, write_file
from skills_loader import SkillsLoader

# Persistence Tests
def test_persistence(tmp_path):
    db_path = str(tmp_path / "test.db")
    p = Persistence(db_path)
    p.add_history("chat1", "user1", "user", "Hello")
    p.add_history("chat1", "user1", "assistant", "Hi")
    history = p.get_history("chat1", "user1")
    assert len(history) == 2
    assert history[0]["role"] == "user"

    p.set_state("k", "v")
    assert p.get_state("k") == "v"
    assert p.get_state("nonexistent", default="def") == "def"

# Config Tests
def test_config(tmp_path):
    cfg_file = tmp_path / "agent.json"
    cfg_data = {
        "gemini_api_key": "test_key",
        "redis_url": "redis://localhost",
        "mcp_servers": []
    }
    cfg_file.write_text(json.dumps(cfg_data))
    config = load_config(str(cfg_file))
    assert config.gemini_api_key == "test_key"
    assert config.heartbeat_interval_minutes == 5 # default

# Bus Tests
@pytest.mark.asyncio
async def test_bus():
    bus = MessageBus("redis://localhost")
    bus.redis = fakeredis.FakeRedis(decode_responses=True)
    bus.pubsub = bus.redis.pubsub()

    received = []
    async def callback(msg):
        received.append(msg)

    await bus.subscribe_to_commands("cmd", callback)
    await asyncio.sleep(0.1)
    await bus.publish_response("cmd", {"data": "test"})
    await asyncio.sleep(0.2)
    assert len(received) == 1
    assert received[0]["data"] == "test"
    await bus.stop()

# Internal Tools Tests
def test_tools_internal(tmp_path):
    test_file = tmp_path / "test.txt"
    assert "Successfully wrote" in write_file(str(test_file), "hello")
    assert read_file(str(test_file)) == "hello"
    assert str(test_file.name) in list_files(str(tmp_path))
    assert "STDOUT:\nechoed\n" in run_shell_command("echo echoed")

# Skills Loader Tests
def test_skills_loader(tmp_path):
    skill_dir = tmp_path / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# My Skill")
    (skill_dir / "res.txt").write_text("resource")

    loader = SkillsLoader(str(tmp_path))
    prompt = loader.load_skills()
    assert "My Skill" in prompt

    res = loader.get_skill_resources("skill1")
    assert res["res.txt"] == "resource"
