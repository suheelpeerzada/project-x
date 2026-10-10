from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.persistence.config_store import load_config, update_active_model
from app.services.llm import call_llm, stream_llm
from app.manifest.system import system_state
from app.persistence import history_store
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Main chat endpoint.
    Backend is authoritative:
    - Uses stored config
    - Uses active model from registry
    - Updates auth_ok
    """

    config = load_config()
    if not config:
        raise HTTPException(
            status_code=400,
            detail="System not configured. Run setup first."
        )

    if not req.messages or not req.messages[-1].content.strip():
        raise HTTPException(
            status_code=400,
            detail="Empty message"
        )

    # -------------------------
    # Resolve active model
    # -------------------------
    models = config.get("models")
    active_id = config.get("active_model_id")

    if not models or not active_id or active_id not in models:
        raise HTTPException(
            status_code=400,
            detail="Active model not configured"
        )

    active_model = models[active_id]

    last_message = req.messages[-1].content

    try:
        reply = call_llm(
            provider=active_model["provider"],
            model=active_model["model"],
            api_key=active_model.get("api_key"),
            message=last_message,
        )

        # Only write to disk when state actually changes
        if active_model.get("auth_ok") is not True or active_model.get("last_error"):
            update_active_model(config, {"auth_ok": True, "last_error": None})
            system_state.load()

        return ChatResponse(content=reply)

    except HTTPException as e:
        if e.status_code == 401:
            update_active_model(config, {
                "auth_ok": False,
                "last_error": {"code": "invalid_key", "message": str(e.detail)},
            })
            system_state.load()
        elif e.status_code == 404:
            update_active_model(config, {
                "last_error": {"code": "model_unavailable", "message": str(e.detail)},
            })
            system_state.load()
        # 429 / 502 / 503: transient, so state is untouched (your rule)
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {type(e).__name__}: {e}",
        ) from e
    
def _persist_reply(stream, conversation_id: str, model: str):
    """Pass chunks through, then save the reply (even a partial one if the client left)."""
    parts = []
    try:
        for chunk in stream:
            parts.append(chunk)
            yield chunk
    finally:
        text = "".join(parts)
        if text.strip():
            history_store.add_message(conversation_id, "assistant", text, model)


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="System not configured. Run setup first.")
    if not req.messages or not req.messages[-1].content.strip():
        raise HTTPException(status_code=400, detail="Empty message")

    models = config.get("models")
    active_id = config.get("active_model_id")
    if not models or not active_id or active_id not in models:
        raise HTTPException(status_code=400, detail="Active model not configured")
    active_model = models[active_id]

    new_message = req.messages[-1].content

    # Context comes from the saved conversation (backend = source of truth)
    conv_id = req.conversation_id
    if conv_id:
        if not history_store.conversation_exists(conv_id):
            raise HTTPException(status_code=404, detail="Conversation not found")
        messages = history_store.get_llm_messages(conv_id) + [
            {"role": "user", "content": new_message}
        ]
    else:
        messages = [{"role": m.role, "content": m.content} for m in req.messages]

    try:
        stream = stream_llm(
            active_model["provider"],
            active_model["model"],
            active_model.get("api_key"),
            messages,
        )
    except HTTPException as e:
        if e.status_code == 401:
            update_active_model(config, {
                "auth_ok": False,
                "last_error": {"code": "invalid_key", "message": str(e.detail)},
            })
            system_state.load()
        elif e.status_code == 404:
            update_active_model(config, {
                "last_error": {"code": "model_unavailable", "message": str(e.detail)},
            })
            system_state.load()
        raise

    # Only now (the provider accepted the request) touch the database,
    # so failed requests never leave empty conversations behind.
    if not conv_id:
        conv_id = history_store.create_conversation(
            history_store.title_from(new_message)
        )["id"]
    history_store.add_message(conv_id, "user", new_message)

    return StreamingResponse(
        _persist_reply(stream, conv_id, active_model["model"]),
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Conversation-Id": conv_id,
        },
    )