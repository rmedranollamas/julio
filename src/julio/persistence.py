from google.adk.sessions.sqlite_session_service import (
    SqliteSessionService,
    CREATE_SCHEMA_SQL,
)
import aiosqlite
import asyncio
import json
from contextlib import asynccontextmanager


class OptimizedSqliteSessionService(SqliteSessionService):
    """Subclass of SqliteSessionService that uses a shared connection to avoid overhead."""

    def __init__(self, persistence: "Persistence"):
        super().__init__(db_path=persistence.db_path)
        self.persistence = persistence

    @asynccontextmanager
    async def _get_db_connection(self):
        db = await self.persistence.get_connection()
        yield db


class Persistence:
    """Manager for SQLite connection and ADK Session Service."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()
        self.session_service = OptimizedSqliteSessionService(self)

    async def get_connection(self) -> aiosqlite.Connection:
        """Returns a thread-safe shared connection, initializing schema on first connect."""
        if self._db is not None:
            return self._db

        async with self._lock:
            if self._db is None:
                db = await aiosqlite.connect(self.db_path)
                try:
                    await db.executescript(CREATE_SCHEMA_SQL)
                    await db.commit()
                    self._db = db
                except Exception:
                    await db.close()
                    raise
            return self._db

    async def get_history(self, session_id: str, user_id: str, limit: int = 10):
        """Retrieves recent conversation history from the events table."""
        db = await self.get_connection()
        query = (
            "SELECT event_data FROM events "
            "WHERE session_id = ? AND user_id = ? "
            "ORDER BY timestamp DESC LIMIT ?"
        )
        async with db.execute(query, (session_id, user_id, limit)) as cursor:
            rows = await cursor.fetchall()
            # ADK stores event_data as JSON.
            # Offload JSON deserialization to a thread to avoid blocking the event loop.
            if not rows:
                return []

            def _parse_rows(rows_to_parse):
                return [json.loads(row[0]) for row in rows_to_parse]

            return await asyncio.to_thread(_parse_rows, rows)

    async def close(self):
        """Closes the shared database connection."""
        async with self._lock:
            if self._db:
                await self._db.close()
                self._db = None
