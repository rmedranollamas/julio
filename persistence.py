import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any

class Persistence:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT,
                    user_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

    def add_history(self, source_id: str, user_id: str, role: str, content: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (source_id, user_id, role, content) VALUES (?, ?, ?, ?)",
                (source_id, user_id, role, content)
            )

    def get_history(self, source_id: str, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT role, content FROM history WHERE source_id = ? AND user_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?",
                (source_id, user_id, limit)
            )
            rows = cursor.fetchall()
            # Return in chronological order
            return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

    def set_state(self, key: str, value: Any):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )

    def get_state(self, key: str, default: Any = None) -> Any:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM state WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default
