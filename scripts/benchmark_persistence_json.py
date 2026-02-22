import asyncio
import json
import time
import os
from julio.persistence import Persistence

async def heartbeat(stop_event):
    latencies = []
    while not stop_event.is_set():
        start = time.perf_counter()
        await asyncio.sleep(0.001)
        latencies.append(time.perf_counter() - start - 0.001)
    return latencies

async def run_benchmark():
    db_path = "perf_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    persistence = Persistence(db_path)
    db = await persistence.get_connection()

    # Setup data
    print("Preparing data...")
    await db.execute(
        "INSERT OR IGNORE INTO sessions (app_name, user_id, id, state, create_time, update_time) VALUES (?, ?, ?, ?, ?, ?)",
        ("app", "user1", "session1", "{}", 0, 0)
    )

    # Create a large-ish JSON (500KB)
    large_json_str = json.dumps({"data": "x" * 500000})

    for i in range(50):
        await db.execute(
            "INSERT INTO events (id, app_name, user_id, session_id, invocation_id, timestamp, event_data) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (f"id{i}", "app", "user1", "session1", f"inv{i}", i, large_json_str)
        )
    await db.commit()

    print("Running benchmark...")
    stop_event = asyncio.Event()
    hb_task = asyncio.create_task(heartbeat(stop_event))

    # Give heartbeat a moment to start
    await asyncio.sleep(0.1)

    start_time = time.perf_counter()
    for _ in range(10):
        # Fetch 50 rows, each with 500KB JSON = 25MB of JSON to parse each time
        await persistence.get_history("session1", "user1", limit=50)
    total_time = time.perf_counter() - start_time

    stop_event.set()
    latencies = await hb_task

    print(f"Total time for 10 get_history calls: {total_time:.4f}s")
    print(f"Average time per call: {total_time/10:.4f}s")
    if latencies:
        print(f"Max event loop lag: {max(latencies)*1000:.2f}ms")
        print(f"Avg event loop lag: {(sum(latencies)/len(latencies))*1000:.2f}ms")

    await persistence.close()
    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
