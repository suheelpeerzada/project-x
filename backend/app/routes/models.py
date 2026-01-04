from fastapi import APIRouter, HTTPException, Query
from app.registry.models import (
    get_models_for_provider,
    get_all_models_for_provider,
)
from app.persistence.model_store import add_user_model

router = APIRouter()

@router.get("/models")
def list_models(provider: str = Query(...)):
    try:
        return get_all_models_for_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown provider")

@router.post("/models")
def add_model(payload: dict):
    provider = payload.get("provider")
    model_id = payload.get("id")
    name = payload.get("name")

    if not provider or not model_id or not name:
        raise HTTPException(status_code=400, detail="Missing fields")

    # Validate provider exists
    try:
        get_models_for_provider(provider)
    except KeyError:
        raise HTTPException(status_code=400, detail="Unknown provider")

    model = {
        "id": model_id,
        "name": name,
        "provider": provider,
    }

    # Optional fields (for custom / local)
    if "base_url" in payload:
        model["base_url"] = payload["base_url"]

    add_user_model(model)
    return {"ok": True}