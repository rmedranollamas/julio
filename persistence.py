from google.adk.sessions.sqlite_session_service import SqliteSessionService

class PersistenceWrapper:
    """Wrapper for ADK SqliteSessionService to maintain consistency in AgentService."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        # SqliteSessionService handles its own schema initialization on connect.
        self.session_service = SqliteSessionService(db_path=db_path)
