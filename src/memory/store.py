"""
Memory Store — historial de conversaciones + sesiones Claude en SQLite
"""
import os
import sqlite3
from typing import List, Dict, Optional

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
            # Tabla para persistir session_id del Claude Agent SDK
            # Permite retomar conversaciones entre reinicios del servidor
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claude_sessions (
                    conversation_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv ON messages(conversation_id)")

    # ── Historial de mensajes ──────────────────────────────────────────────

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
            conn.execute("DELETE FROM claude_sessions WHERE conversation_id=?", (conversation_id,))

    # ── Sesiones Claude Agent SDK ──────────────────────────────────────────

    def get_claude_session(self, conversation_id: str) -> Optional[str]:
        """Devuelve el session_id de Claude para retomar la conversación."""
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT session_id FROM claude_sessions WHERE conversation_id=?",
                (conversation_id,)
            ).fetchone()
        return row[0] if row else None

    def set_claude_session(self, conversation_id: str, session_id: str):
        """Guarda o actualiza el session_id de Claude para esta conversación."""
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO claude_sessions (conversation_id, session_id, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    session_id=excluded.session_id,
                    updated_at=CURRENT_TIMESTAMP
            """, (conversation_id, session_id))
