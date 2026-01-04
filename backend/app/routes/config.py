from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.persistence.config_store import (
    load_config,
    save_config,
    reset_config,
    update_config,
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
    # Fresh setup always overwrites config
    config = {
        "provider": payload.provider,
        "model": payload.model_id,   # canonical storage key
        "api_key": payload.api_key.strip(),
        "auth_ok": None,
    }

    save_config(config)
    system_state.load()
    return {"ok": True}


@router.post("/update")
def update_config_route(payload: UpdateConfigRequest):
    config = load_config()

    if not config:
        raise HTTPException(status_code=400, detail="System not configured")

    if payload.model_id is not None:
        config["model"] = payload.model_id

    if payload.api_key is not None and payload.api_key.strip():
        config["api_key"] = payload.api_key.strip()
        config["auth_ok"] = None  # reset auth until verified

    save_config(config)
    system_state.load()
    return {"ok": True}


@router.post("/verify")
def verify_api_key():
    """
    Explicit API key verification.
    This is the ONLY legal way to unlock chat.
    """

    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="System not configured")

    try:
        # Cheap validation call
        call_llm(
            provider=config["provider"],
            model=config["model"],
            api_key=config.get("api_key"),
            message="ping",
        )

        update_config({"auth_ok": True})
        system_state.load()
        return {"ok": True}

    except HTTPException:
        update_config({"auth_ok": False})
        system_state.load()
        raise


@router.post("/reset")
def reset_system_config():
    reset_config()
    system_state._reset()
    return {"ok": True}
