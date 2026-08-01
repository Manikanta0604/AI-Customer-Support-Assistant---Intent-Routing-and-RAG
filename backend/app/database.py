import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .schemas import Escalation, Message


class Database:
    def __init__(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, unresolved_count INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL,
                    content TEXT NOT NULL, intent TEXT, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS escalations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, reason TEXT NOT NULL,
                    customer_message TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL
                );
            """)

    def ensure_session(self, session_id: str | None) -> str:
        value = session_id or str(uuid.uuid4())
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO sessions(id, created_at) VALUES (?, ?)", (value, _now()))
        return value

    def add_message(self, session_id: str, role: str, content: str, intent: str | None = None) -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO messages(session_id, role, content, intent, created_at) VALUES (?, ?, ?, ?, ?)",
                (session_id, role, content, intent, _now()),
            )
            return int(cursor.lastrowid)

    def history(self, session_id: str, limit: int = 12) -> list[Message]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT id, role, content, intent, created_at FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [Message(**dict(row)) for row in reversed(rows)]

    def unresolved_count(self, session_id: str) -> int:
        with self.connect() as db:
            row = db.execute("SELECT unresolved_count FROM sessions WHERE id=?", (session_id,)).fetchone()
        return int(row[0]) if row else 0

    def mark_unresolved(self, session_id: str, unresolved: bool) -> None:
        with self.connect() as db:
            if unresolved:
                db.execute("UPDATE sessions SET unresolved_count=unresolved_count+1 WHERE id=?", (session_id,))
            else:
                db.execute("UPDATE sessions SET unresolved_count=0 WHERE id=?", (session_id,))

    def escalate(self, session_id: str, reason: str, customer_message: str) -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO escalations(session_id, reason, customer_message, created_at) VALUES (?, ?, ?, ?)",
                (session_id, reason, customer_message, _now()),
            )
            return int(cursor.lastrowid)

    def escalations(self) -> list[Escalation]:
        with self.connect() as db:
            rows = db.execute("SELECT * FROM escalations ORDER BY id DESC").fetchall()
        return [Escalation(**dict(row)) for row in rows]

    def update_escalation(self, case_id: int, status: str) -> bool:
        with self.connect() as db:
            cursor = db.execute("UPDATE escalations SET status=? WHERE id=?", (status, case_id))
            return cursor.rowcount > 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
