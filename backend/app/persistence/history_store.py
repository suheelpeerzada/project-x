"""
SQLite-backed chat history + attachment records (local-first, no extra deps).

Lives in its own file (~/.project_x_history.db), separate from the config,
so resetting the config does not delete conversations.
Uploaded files live in ~/.project_x_files/.
API keys are never stored here.
"""
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path.home() / ".project_x_history.db"
FILES_DIR = Path.home() / ".project_x_files"

# Max characters of extracted file text sent to the model per message.
# (~2.2K tokens: fits the free-tier 8K tokens/minute budget with room for a reply.)
TEXT_BUDGET_CHARS = 9000

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

        -- Uploaded files. Rows start unattached (message_id NULL) and are
        -- linked to a message when the chat request that uses them succeeds.
        CREATE TABLE IF NOT EXISTS attachments (
            id              TEXT PRIMARY KEY,
            conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
            message_id      TEXT REFERENCES messages(id) ON DELETE CASCADE,
            kind            TEXT NOT NULL,      -- image | document | audio
            filename        TEXT NOT NULL,      -- display name only
            mime            TEXT NOT NULL,
            size            INTEGER NOT NULL,
            path            TEXT NOT NULL,      -- file name inside FILES_DIR
            text            TEXT,               -- extracted text / transcript
            note            TEXT,               -- e.g. "3 of 20 pages read"
            created_at      TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_att_conv ON attachments(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_att_msg  ON attachments(message_id);
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


def _unlink(stored_name: str) -> None:
    """Delete a stored file. Only the bare file name is used (no path traversal)."""
    try:
        (FILES_DIR / Path(stored_name).name).unlink(missing_ok=True)
    except OSError:
        pass


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


def public_attachment(att: Dict[str, Any]) -> Dict[str, Any]:
    """What the frontend may see (never the stored path or the extracted text)."""
    return {
        "id": att["id"],
        "kind": att["kind"],
        "filename": att["filename"],
        "mime": att["mime"],
        "size": att["size"],
        "note": att.get("note"),
    }


def attachment_text_block(att: Dict[str, Any]) -> str:
    """
    Text of a document / transcript, fenced so the model can tell it is
    untrusted file content and not instructions.
    """
    label = {"document": "document", "audio": "voice note transcript"}.get(
        att["kind"], "file"
    )
    note = f" ({att['note']})" if att.get("note") else ""
    name = att["filename"].replace("\n", " ")[:120]
    body = (att.get("text") or "").replace("<<<", "‹‹‹").replace(">>>", "›››")
    return (
        f'\n\n<<<BEGIN ATTACHMENT: {label} "{name}"{note}>>>\n'
        f"{body}\n<<<END ATTACHMENT>>>"
    )


def fit_text_budget(
    atts: List[Dict[str, Any]], budget: int = TEXT_BUDGET_CHARS
) -> List[Dict[str, Any]]:
    """Return copies where the combined extracted text fits the budget."""
    out = [dict(a) for a in atts]
    texty = [a for a in out if a["kind"] != "image" and a.get("text")]
    if not texty:
        return out
    per = max(500, budget // len(texty))
    for a in texty:
        if len(a["text"]) > per:
            a["text"] = a["text"][:per]
            cut = f"cut to the first {per} characters to fit the token budget"
            a["note"] = f"{a['note']}; {cut}" if a.get("note") else cut
    return out


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


def _attachments_by_message(con, conversation_id: str) -> Dict[str, List[Dict[str, Any]]]:
    rows = con.execute(
        "SELECT * FROM attachments WHERE conversation_id = ? AND message_id IS NOT NULL "
        "ORDER BY created_at",
        (conversation_id,),
    ).fetchall()
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in rows:
        grouped.setdefault(r["message_id"], []).append(dict(r))
    return grouped


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
        atts = _attachments_by_message(con, conversation_id)
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
                "attachments": [public_attachment(a) for a in atts.get(m["id"], [])],
            }
            for m in msgs
        ],
    }


def get_llm_messages(conversation_id: str) -> List[Dict[str, str]]:
    """
    Saved messages in the shape the LLM layer expects.
    Documents / transcripts are re-attached as fenced text; images are NOT
    re-sent (too many tokens), only mentioned by name.
    """
    with _conn() as con:
        rows = con.execute(
            "SELECT id, role, content FROM messages WHERE conversation_id = ? ORDER BY seq",
            (conversation_id,),
        ).fetchall()
        atts = _attachments_by_message(con, conversation_id)

    out = []
    for r in rows:
        content = r["content"]
        for a in atts.get(r["id"], []):
            if a["kind"] == "image":
                content += f'\n\n[The user attached an image: "{a["filename"]}"]'
            else:
                content += attachment_text_block(a)
        out.append({"role": r["role"], "content": content})
    return out


def rename_conversation(conversation_id: str, title: str) -> bool:
    with _conn() as con:
        cur = con.execute(
            "UPDATE conversations SET title = ? WHERE id = ?",
            (title, conversation_id),
        )
        return cur.rowcount > 0


def delete_conversation(conversation_id: str) -> bool:
    with _conn() as con:
        paths = [
            r["path"]
            for r in con.execute(
                "SELECT path FROM attachments WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchall()
        ]
        cur = con.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        deleted = cur.rowcount > 0
    if deleted:
        for p in paths:
            _unlink(p)
    return deleted


def clear_all() -> None:
    with _conn() as con:
        paths = [r["path"] for r in con.execute("SELECT path FROM attachments").fetchall()]
        con.execute("DELETE FROM conversations")  # messages + attachments cascade
        con.execute("DELETE FROM attachments")    # also unattached uploads
    for p in paths:
        _unlink(p)


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


# ----------------------------
# Attachments
# ----------------------------

def add_attachment(
    att_id: str,
    kind: str,
    filename: str,
    mime: str,
    size: int,
    path: str,
    text: Optional[str] = None,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    now = _now()
    with _conn() as con:
        con.execute(
            "INSERT INTO attachments (id, kind, filename, mime, size, path, text, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (att_id, kind, filename, mime, size, path, text, note, now),
        )
    return {
        "id": att_id, "kind": kind, "filename": filename, "mime": mime,
        "size": size, "path": path, "text": text, "note": note,
        "conversation_id": None, "message_id": None, "created_at": now,
    }


def get_attachment(att_id: str) -> Optional[Dict[str, Any]]:
    with _conn() as con:
        row = con.execute("SELECT * FROM attachments WHERE id = ?", (att_id,)).fetchone()
    return dict(row) if row else None


def get_unattached(ids: List[str]) -> List[Dict[str, Any]]:
    """Uploaded-but-unused attachments, in the requested order. Missing/used ids are skipped."""
    found = []
    for att_id in dict.fromkeys(ids):          # de-duplicate, keep order
        att = get_attachment(att_id)
        if att and att["message_id"] is None:
            found.append(att)
    return found


def attach_to_message(
    atts: List[Dict[str, Any]], conversation_id: str, message_id: str
) -> None:
    """Link attachments to a message (also saves any budget-trimmed text/note)."""
    with _conn() as con:
        for a in atts:
            con.execute(
                "UPDATE attachments SET conversation_id = ?, message_id = ?, text = ?, note = ? "
                "WHERE id = ? AND message_id IS NULL",
                (conversation_id, message_id, a.get("text"), a.get("note"), a["id"]),
            )


def delete_unattached(att_id: str) -> str:
    """Returns 'deleted', 'missing' or 'attached'."""
    att = get_attachment(att_id)
    if not att:
        return "missing"
    if att["message_id"] is not None:
        return "attached"
    with _conn() as con:
        con.execute("DELETE FROM attachments WHERE id = ?", (att_id,))
    _unlink(att["path"])
    return "deleted"


def purge_orphans(max_age_hours: int = 24) -> int:
    """Remove uploads that were never sent in a message."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_age_hours)).isoformat()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, path FROM attachments WHERE message_id IS NULL AND created_at < ?",
            (cutoff,),
        ).fetchall()
        for r in rows:
            con.execute("DELETE FROM attachments WHERE id = ?", (r["id"],))
    for r in rows:
        _unlink(r["path"])
    return len(rows)
