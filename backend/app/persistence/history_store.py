"""
SQLite-backed chat history (local-first, no extra dependencies).

Lives in its own file (~/.project_x_history.db), separate from the config,
so resetting the config does not delete conversations.
API keys are never stored here.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path.home() / ".project_x_history.db"

_initialized_for: Optional[Path] = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _init(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id         TEXT PRIMARY KEY,
            title      TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            seq             INTEGER PRIMARY KEY AUTOINCREMENT,
            id              TEXT NOT NULL UNIQUE,
            conversation_id TEXT NOT NULL
                REFERENCES conversations(id) ON DELETE CASCADE,
            role            TEXT NOT NULL,
            content         TEXT NOT NULL,
            model           TEXT,
            created_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conv
            ON messages(conversation_id, seq);
        CREATE INDEX IF NOT EXISTS idx_conv_updated
            ON conversations(updated_at DESC);
        """
    )


@contextmanager
def _conn():
    """One short-lived connection per call (safe across FastAPI worker threads)."""
    global _initialized_for
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        if _initialized_for != DB_PATH:
            _init(con)
            _initialized_for = DB_PATH
        yield con
        con.commit()
    finally:
        con.close()


# ----------------------------
# Helpers
# ----------------------------

def title_from(text: str, limit: int = 50) -> str:
    """First line of the first message, whitespace collapsed, trimmed."""
    first = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    first = " ".join(first.split())
    if not first:
        return "New chat"
    return first if len(first) <= limit else first[: limit - 1].rstrip() + "…"


# ----------------------------
# Conversations
# ----------------------------

def create_conversation(title: str = "New chat") -> Dict[str, Any]:
    cid, now = str(uuid.uuid4()), _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO conversations (id, title, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (cid, title, now, now),
        )
    return {"id": cid, "title": title, "timestamp": now}


def conversation_exists(conversation_id: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return row is not None


def list_conversations() -> List[Dict[str, Any]]:
    """Newest first, shaped for the Sidebar (id, title, preview, timestamp)."""
    with _conn() as con:
        rows = con.execute(
            """
            SELECT c.id, c.title, c.updated_at AS timestamp,
                   (SELECT content FROM messages m
                     WHERE m.conversation_id = c.id
                     ORDER BY m.seq DESC LIMIT 1) AS preview
              FROM conversations c
             ORDER BY c.updated_at DESC
            """
        ).fetchall()
    out = []
    for r in rows:
        preview = " ".join((r["preview"] or "").split())[:100]
        out.append(
            {
                "id": r["id"],
                "title": r["title"],
                "preview": preview,
                "timestamp": r["timestamp"],
            }
        )
    return out


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as con:
        conv = con.execute(
            "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ?",
            (conversation_id,),
        ).fetchone()
        if not conv:
            return None
        msgs = con.execute(
            "SELECT id, role, content, model, created_at FROM messages "
            "WHERE conversation_id = ? ORDER BY seq",
            (conversation_id,),
        ).fetchall()
    return {
        "id": conv["id"],
        "title": conv["title"],
        "messages": [
            {
                "id": m["id"],
                "role": m["role"],
                "content": m["content"],
                "model": m["model"],
                "timestamp": m["created_at"],
            }
            for m in msgs
        ],
    }


def get_llm_messages(conversation_id: str) -> List[Dict[str, str]]:
    """Saved messages in the shape the LLM layer expects."""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY seq",
            (conversation_id,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def rename_conversation(conversation_id: str, title: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id),
        )
        return cur.rowcount > 0


def delete_conversation(conversation_id: str) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cur.rowcount > 0


def clear_all() -> None:
    with _conn() as con:
        con.execute("DELETE FROM conversations")  # messages cascade


# ----------------------------
# Messages
# ----------------------------

def add_message(
    conversation_id: str, role: str, content: str, model: Optional[str] = None
) -> str:
    mid, now = str(uuid.uuid4()), _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO messages (id, conversation_id, role, content, model, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mid, conversation_id, role, content, model, now),
        )
        con.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
    return mid
