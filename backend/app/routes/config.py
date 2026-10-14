from fastapi import APIRouter, HTTPException, Depends
from app.security import chat_limiter, provider_limiter, config_limiter, validate_base_url
from pydantic import BaseModel
from typing import Optional
import uuid

from app.persistence.config_store import (
    load_config,
    save_config,
    reset_config,
    ensure_registry,
    get_active_model,
    update_active_model,
)
from app.manifest.system import system_state
from app.services.llm import call_llm, verify_model

router = APIRouter(prefix="/config", tags=["config"])

class UpdateConfigRequest(BaseModel):
    model_id: Optional[str] = None
    api_key: Optional[str] = None


class SetupConfigRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str
    base_url: Optional[str] = None


@router.post("/setup")
def setup_config(payload: SetupConfigRequest):
    """
    Fresh setup.
    Creates a registry with a single active model.
    """
    model_uuid = str(uuid.uuid4())

    entry = {
        "provider": payload.provider,
        "model": payload.model_id,
        "api_key": payload.api_key.strip(),
        "auth_ok": None,
        "last_error": None,
    }
    if payload.provider == "custom-openai":
        try:
            entry["base_url"] = validate_base_url(payload.base_url or "")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid base URL: {e}")

    config = {"models": {model_uuid: entry}, "active_model_id": model_uuid}
    save_config(config)
    system_state.load()
    return {"ok": True}


@router.post("/update")
def update_config_route(payload: UpdateConfigRequest):
    """
    Update active model fields only.
    Backward-compatible with legacy configs.
    """
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="System not configured")

    # Ensure registry exists (may persist migration)
    config = ensure_registry(config)

    patch = {}

    # if payload.model_id is not None:
    #     patch["model"] = payload.model_id

    if payload.api_key is not None and payload.api_key.strip():
        # Always update API key if user provides one
        patch["api_key"] = payload.api_key.strip()
        patch["auth_ok"] = None
        patch["last_error"]= None

    if patch:
        update_active_model(config, patch)

    system_state.load()
    return {"ok": True}


@router.post("/verify", dependencies=[Depends(config_limiter)])
def verify_api_key():
    """
    Explicit API key verification.
    This is the ONLY legal way to unlock chat.
    Operates on the active model.
    """
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="System not configured")

    # Ensure registry exists (may persist migration)
    config = ensure_registry(config)

    active = get_active_model(config)
    if not active:
        raise HTTPException(status_code=400, detail="Active model not found")

    try:
        verify_model(active["provider"], active["model"], active.get("api_key"), active.get("base_url"))
        update_active_model(config, {"auth_ok": True, "last_error": None})
        system_state.load()
        return {"ok": True, "verified": True}

    except HTTPException as e:
        if e.status_code == 401:
            update_active_model(config, {
                "auth_ok": False,
                "last_error": {"code": "invalid_key", "message": e.detail},
            })
            system_state.load()
            raise
        if e.status_code == 404:
            # Key is valid, model is gone
            update_active_model(config, {
                "auth_ok": True,
                "last_error": {"code": "model_unavailable", "message": e.detail},
            })
            system_state.load()
            return {"ok": True, "verified": False, "detail": e.detail}
        return {"ok": True, "verified": False, "detail": e.detail}

@router.post("/reset")
def reset_system_config():
    reset_config()
    system_state._reset()
    return {"ok": True}
