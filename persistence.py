from google.adk.sessions.sqlite_session_service import SqliteSessionService
import aiosqlite
import json

class PersistenceWrapper:
    """Wrapper for ADK SqliteSessionService to maintain consistency in AgentService."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        # SqliteSessionService handles its own schema initialization on connect.
        self.session_service = SqliteSessionService(db_path=db_path)

    async def get_history(self, source_id: str, user_id: str):
        """Asynchronous database call to get history."""
        # Use aiosqlite for non-blocking DB calls
        async with aiosqlite.connect(self.db_path) as db:
            query = "SELECT event_data FROM events WHERE session_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 10"
            async with db.execute(query, (source_id, user_id)) as cursor:
                rows = await cursor.fetchall()
                history = [json.loads(row[0]) for row in rows]

        return history
