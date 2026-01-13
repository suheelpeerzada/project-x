from fastapi import APIRouter, HTTPException
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
from app.services.llm import call_llm

router = APIRouter(prefix="/config", tags=["config"])


class UpdateConfigRequest(BaseModel):
    model_id: Optional[str] = None
    api_key: Optional[str] = None


class SetupConfigRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str


@router.post("/setup")
def setup_config(payload: SetupConfigRequest):
    """
    Fresh setup.
    Creates a registry with a single active model.
    """
    model_uuid = str(uuid.uuid4())

    config = {
        "models": {
            model_uuid: {
                "provider": payload.provider,
                "model": payload.model_id,
                "api_key": payload.api_key.strip(),
                "auth_ok": None,
            }
        },
        "active_model_id": model_uuid,
    }

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

    if payload.model_id is not None:
        patch["model"] = payload.model_id

    if payload.api_key is not None and payload.api_key.strip():
        active = get_active_model(config)
        if not active:
            raise HTTPException(status_code=400, detail="Active model not found")

        if payload.api_key.strip() != active.get("api_key"):
            patch["api_key"] = payload.api_key.strip()
            patch["auth_ok"] = None

    if patch:
        update_active_model(config, patch)

    system_state.load()
    return {"ok": True}


@router.post("/verify")
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
        # Cheap validation call
        call_llm(
            provider=active["provider"],
            model=active["model"],
            api_key=active.get("api_key"),
            message="ping",
        )

        update_active_model(config, {"auth_ok": True})
        system_state.load()
        return {"ok": True}

    except HTTPException:
        update_active_model(config, {"auth_ok": False})
        system_state.load()
        raise


@router.post("/reset")
def reset_system_config():
    reset_config()
    system_state._reset()
    return {"ok": True}
