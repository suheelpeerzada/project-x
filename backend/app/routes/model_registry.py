from fastapi import APIRouter, HTTPException
from app.schemas.models import AddModelRequest, SwitchModelRequest
from app.persistence.config_store import (
    load_config,
    ensure_registry,
    get_model_by_provider_and_name,
    overwrite_model,
    insert_new_model,
    switch_model,
)
from app.manifest.system import system_state

router = APIRouter()

@router.post("/config/models/add")
def add_model(payload: AddModelRequest):
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="Config not initialized")

    config = ensure_registry(config)

    # Reuse a saved key for the same provider if none was supplied
    api_key = (payload.api_key or "").strip()
    if not api_key:
        for entry in (config.get("models") or {}).values():
            if entry.get("provider") == payload.provider and entry.get("api_key"):
                api_key = entry["api_key"]
                break
    if not api_key and payload.provider != "local":
        raise HTTPException(
            status_code=400,
            detail=f"An API key is required for {payload.provider}",
        )

    existing = get_model_by_provider_and_name(config, payload.provider, payload.model)

    if existing:
        model_id, _ = existing
        overwrite_model(config, model_id, payload.provider, payload.model, api_key)
        system_state.load()
        return {"model_id": model_id, "message": "Model overwritten"}

    new_id = insert_new_model(config, payload.provider, payload.model, api_key)
    system_state.load()
    return {"model_id": new_id, "message": "Model added"}


@router.post("/config/models/switch")
def switch_active_model(payload: SwitchModelRequest):
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="Config not initialized")

    config = ensure_registry(config)

    try:
        active_id = switch_model(config, payload.model_id)
    except RuntimeError:
        raise HTTPException(status_code=400, detail="Model ID not found")

    system_state.load()
    return {"active_model_id": active_id, "message": "Active model switched"}
@router.get("/config/models")
def list_models():
    """
    Return all models in registry with human-readable names and meta.
    """
    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="Config not initialized")

    config = ensure_registry(config)

    models = config.get("models", {})
    active_id = config.get("active_model_id")

    formatted = []

    for model_id, entry in models.items():
        provider = entry.get("provider")
        model = entry.get("model")

        # ---- Human-readable name (same style as system_state) ----
        provider_label = provider.capitalize() if provider else ""
        model_label = model.replace("-", " ").replace("_", " ").title()

        display_name = f"{provider_label} · {model_label}"

        formatted.append({
            "id": model_id,
            "provider": provider,
            "model": model,
            "name": display_name,
            "meta": {
                "size": entry.get("size"),
                "quantization": entry.get("quantization"),
            },
            "is_active": (model_id == active_id)
        })

    return formatted

@router.post("/config/models/delete")
def delete_model(payload: dict):
    """
    Delete a model from the registry.
    Rules:
    - Active model cannot be deleted
    - On success: return updated model list
    """
    model_id = payload.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    config = load_config()
    if not config:
        raise HTTPException(status_code=400, detail="Config not initialized")

    config = ensure_registry(config)

    models = config.get("models", {})
    active_id = config.get("active_model_id")

    # ---- Rule 1: cannot delete active model ----
    if model_id == active_id:
        raise HTTPException(status_code=400, detail="Cannot delete active model")

    # ---- Ensure model exists ----
    if model_id not in models:
        raise HTTPException(status_code=404, detail="Model not found")

    # ---- Delete model ----
    del models[model_id]

    # Persist changes
    from app.persistence.config_store import save_config
    save_config(config)

    # ---- Return updated list (same format as GET /config/models) ----
    formatted = []
    for mid, entry in models.items():
        provider = entry.get("provider")
        model = entry.get("model")

        provider_label = provider.capitalize() if provider else ""
        model_label = model.replace("-", " ").replace("_", " ").title()
        display_name = f"{provider_label} · {model_label}"

        formatted.append({
            "id": mid,
            "provider": provider,
            "model": model,
            "name": display_name,
            "meta": {
                "size": entry.get("size"),
                "quantization": entry.get("quantization"),
            },
            "is_active": (mid == active_id)
        })

    return {"ok": True, "models": formatted}