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

    # Ensure requested model matches active model
    active_model = config.get("model")
    if req.model_id != active_model:
        raise HTTPException(
            status_code=400,
            detail="Requested model does not match active model"
        )

    last_message = req.messages[-1].content

    try:
        reply = call_llm(
            provider=config["provider"],
            model=config["model"],
            api_key=config.get("api_key"),
            message=last_message,
        )

        # Mark auth OK on success
        update_config({"auth_ok": True})
        system_state.auth_ok = True


        return ChatResponse(content=reply)

    except HTTPException:
        # Let FastAPI HTTP errors pass through
        update_config({"auth_ok": False})
        system_state.auth_ok = False

        raise

    except Exception as e:
        # Auth / provider / quota failures end up here
        update_config({"auth_ok": False})
        system_state.auth_ok = False


        raise HTTPException(
            status_code=401,
            detail="Authentication failed or API key invalid"
        ) from e
