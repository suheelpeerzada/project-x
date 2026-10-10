from fastapi import APIRouter
from app.registry.providers import get_available_providers
from typing import Optional
from pydantic import BaseModel
from app.persistence.config_store import load_config
from app.services.llm import list_models

router = APIRouter()

@router.get("/providers")
def list_providers():
    return get_available_providers()

class ListModelsRequest(BaseModel):
    provider: str
    api_key: Optional[str] = None   # omitted → reuse a saved key for this provider


@router.post("/providers/models")
def provider_models(payload: ListModelsRequest):
    key = payload.api_key
    config = load_config() or {}
    added = set()
    for entry in (config.get("models") or {}).values():
        if entry.get("provider") == payload.provider:
            added.add(entry.get("model"))
            key = key or entry.get("api_key")

    models = list_models(payload.provider, key)
    for m in models:
        m["already_added"] = m["id"] in added
        m["free"] = None        # see note below
    return {"provider": payload.provider, "models": models}