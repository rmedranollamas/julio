from google.adk.sessions.sqlite_session_service import SqliteSessionService
import aiosqlite
import json

class PersistenceWrapper:
    """Wrapper for ADK SqliteSessionService to maintain consistency in AgentService."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        # SqliteSessionService handles its own schema initialization on connect.
        self.session_service = SqliteSessionService(db_path=db_path)
        self._db = None

    async def _get_db(self):
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
        return self._db

    async def get_history(self, source_id: str, user_id: str):
        """Asynchronous database call to get history."""
        db = await self._get_db()
        query = "SELECT event_data FROM events WHERE session_id = ? AND user_id = ? ORDER BY timestamp DESC LIMIT 10"
        async with db.execute(query, (source_id, user_id)) as cursor:
            rows = await cursor.fetchall()
            history = [json.loads(row[0]) for row in rows]

        return history

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None
