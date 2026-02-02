import json
import sqlite3
from typing import List, Dict, Any, Optional
import aiosqlite
from contextlib import asynccontextmanager
from google.adk.sessions.sqlite_session_service import SqliteSessionService, PRAGMA_FOREIGN_KEYS, CREATE_SCHEMA_SQL

class OptimizedSqliteSessionService(SqliteSessionService):
    """Subclass of SqliteSessionService that uses a shared connection to avoid overhead."""
    def __init__(self, db_path: str, persistence: 'Persistence'):
        super().__init__(db_path=db_path)
        self.persistence = persistence

    @asynccontextmanager
    async def _get_db_connection(self):
        db = await self.persistence.get_connection()
        # We don't run CREATE_SCHEMA_SQL here because it's already done once in Persistence.get_connection
        yield db

class Persistence:
    """Wrapper for ADK SqliteSessionService to maintain consistency in AgentService."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self.session_service = OptimizedSqliteSessionService(db_path=db_path, persistence=self)

    async def get_connection(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.db_path)
            self._db.row_factory = aiosqlite.Row
            # Initialize schema once
            await self._db.execute(PRAGMA_FOREIGN_KEYS)
            await self._db.executescript(CREATE_SCHEMA_SQL)
            await self._db.commit()
        return self._db

    async def close(self):
        if self._db:
            await self._db.close()
            self._db = None

    async def get_history(self, session_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        db = await self.get_connection()
        # ADK schema has events in 'events' table.
        # app_name is hardcoded to 'agent_service_app' in AgentService,
        # but let's try to find it or assume it.
        # Actually, in main.py: Runner(app_name="agent_service_app", ...)
        app_name = "agent_service_app"

        async with db.execute(
            "SELECT event_data FROM events WHERE app_name=? AND user_id=? AND session_id=? ORDER BY timestamp DESC LIMIT ?",
            (app_name, user_id, session_id, limit)
        ) as cursor:
            rows = await cursor.fetchall()
            return [json.loads(row["event_data"]) for row in rows]
