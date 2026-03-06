"""
Memory Store — historial de conversaciones en SQLite
"""
import os
import sqlite3
from typing import List, Dict

DB_PATH = os.getenv("MEMORY_DB_PATH", "data/memory.db")


class MemoryStore:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv ON messages(conversation_id)")

    def get_history(self, conversation_id: str, max_messages: int = 20) -> List[Dict]:
        with sqlite3.connect(DB_PATH) as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",
                (conversation_id, max_messages)
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def add_message(self, conversation_id: str, role: str, content: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                "INSERT INTO messages (conversation_id, role, content) VALUES (?,?,?)",
                (conversation_id, role, content)
            )

    def clear_conversation(self, conversation_id: str):
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
