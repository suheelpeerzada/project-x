from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.persistence.config_store import load_config, update_config
from app.services.llm import call_llm
from app.manifest.system import system_state

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

        # Mark auth OK on success
        update_config({"auth_ok": True})
        system_state.auth_ok = True

        return ChatResponse(content=reply)

    except HTTPException:
        # Provider / request errors
        update_config({"auth_ok": False})
        system_state.auth_ok = False
        raise

    except Exception as e:
        # Auth / provider / quota failures
        update_config({"auth_ok": False})
        system_state.auth_ok = False

        raise HTTPException(
            status_code=401,
            detail="Authentication failed or API key invalid"
        ) from e
