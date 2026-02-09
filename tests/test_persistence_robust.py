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

    # The schema is already created by p.get_connection()
    async with p.session_service._get_db_connection() as conn:
        # We also need a session to satisfy foreign key constraints if they are enabled
        await conn.execute(
            "INSERT INTO sessions (app_name, user_id, id, state, create_time, update_time) VALUES (?, ?, ?, ?, ?, ?)",
            ("app1", "uid1", "sid1", "{}", 0, 0)
        )

        event_data = {"role": "user", "content": "hello"}
        await conn.execute(
            "INSERT INTO events (id, app_name, user_id, session_id, invocation_id, timestamp, event_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("eid1", "app1", "uid1", "sid1", "inv1", 1000.0, json.dumps(event_data))
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
