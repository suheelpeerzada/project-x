from typing import List, Dict
from app.persistence.model_store import load_user_models


# Static, validated model lists per provider adapter
_PROVIDER_MODELS: dict[str, List[Dict[str, str]]] = {
    "groq": [
        {
            "id": "llama-3.1-8b-instant",
            "name": "LLaMA 3.1 (8B Instant)",
        },
        {
            "id": "llama-3.1-70b-versatile",
            "name": "LLaMA 3.1 (70B Versatile)",
        },
    ],
    "openai": [
        {
            "id": "gpt-4o-mini",
            "name": "GPT-4o Mini",
        },
        {
            "id": "gpt-4o",
            "name": "GPT-4o",
        },
    ],
    # Adapters with no predefined models yet
    "local": [],
    "custom-openai": [],
}

def get_models_for_provider(provider: str) -> List[Dict[str, str]]:
    if provider not in _PROVIDER_MODELS:
        raise KeyError(f"Unknown provider: {provider}")
    return _PROVIDER_MODELS[provider]

def get_all_models_for_provider(provider: str):
    builtin = get_models_for_provider(provider)
    user_models = [
        m for m in load_user_models()
        if m.get("provider") == provider
    ]
    return builtin + user_models

def get_model_by_id(provider: str, model_id: str) -> Dict[str, str] | None:
    """
    Return a single model dict by provider + model_id.
    Includes both built-in and user-added models.
    """
    try:
        models = get_all_models_for_provider(provider)
    except KeyError:
        return None

    for model in models:
        if model.get("id") == model_id:
            return model

    return None
