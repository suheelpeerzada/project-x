from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.persistence import history_store

router = APIRouter(prefix="/history", tags=["history"])


class RenameRequest(BaseModel):
    title: str


@router.get("")
def list_history():
    """All conversations, newest first (shaped for the Sidebar)."""
    return history_store.list_conversations()


@router.get("/{conversation_id}")
def get_history(conversation_id: str):
    """One conversation with its messages."""
    conv = history_store.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}")
def rename_history(conversation_id: str, payload: RenameRequest):
    title = " ".join(payload.title.split())[:80]
    if not title:
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    if not history_store.rename_conversation(conversation_id, title):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True, "title": title}


@router.delete("/{conversation_id}")
def delete_history(conversation_id: str):
    if not history_store.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"ok": True}


@router.delete("")
def clear_history():
    """Delete ALL conversations."""
    history_store.clear_all()
    return {"ok": True}
