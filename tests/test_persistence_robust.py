import pytest
import asyncio
import json
import os
from julio.persistence import Persistence

@pytest.mark.asyncio
async def test_persistence_history(tmp_path):
    db_path = str(tmp_path / "test_persistence.db")
    p = Persistence(db_path)

    # We need to insert some data to test get_history.
    # Since we are using shared connection, we can use p.get_connection()
    db = await p.get_connection()

    # Create table if not exists (usually handled by ADK session service, but let's be sure for the test)
    # Actually, p.session_service._get_db_connection() would trigger it.
    async with p.session_service._get_db_connection() as conn:
        # This should trigger schema creation in SqliteSessionService if we used it correctly.
        # But wait, SqliteSessionService creates it on __init__? No, usually on connection.
        # Let's check ADK if possible, or just manually create for the test.
        await conn.execute("CREATE TABLE IF NOT EXISTS events (session_id TEXT, user_id TEXT, event_data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")

        event_data = {"role": "user", "content": "hello"}
        await conn.execute(
            "INSERT INTO events (session_id, user_id, event_data) VALUES (?, ?, ?)",
            ("sid1", "uid1", json.dumps(event_data))
        )
        await conn.commit()

    history = await p.get_history("sid1", "uid1")
    assert len(history) == 1
    assert history[0]["content"] == "hello"

    await p.close()

@pytest.mark.asyncio
async def test_persistence_shared_connection(tmp_path):
    db_path = str(tmp_path / "test_shared.db")
    p = Persistence(db_path)

    conn1 = await p.get_connection()
    conn2 = await p.get_connection()
    assert conn1 is conn2

    await p.close()
    assert p._db is None
