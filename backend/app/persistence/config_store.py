import json
from pathlib import Path
from typing import Optional, Dict, Any
import uuid

CONFIG_PATH = Path.home() / ".project_x_config.json"


def load_config() -> Optional[Dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return None
    return json.loads(CONFIG_PATH.read_text())


def save_config(data: Dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(data, indent=2))


def reset_config() -> None:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()


def update_config(patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge partial updates into existing config (shallow merge).
    Backward-compatible with legacy single-model config.
    """
    config = load_config()
    if not config:
        raise RuntimeError("Config not initialized")

    config.update(patch)
    save_config(config)
    return config


# ----------------------------
# Phase 1 helpers (registry-safe)
# ----------------------------

def ensure_registry(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ensure the config has a models registry and active_model_id.
    If legacy config is detected, create a registry in-place
    (persisted), preserving existing values.
    """
    if "models" in config and "active_model_id" in config:
        return config

    # Legacy single-model → promote to registry
    provider = config.get("provider")
    model = config.get("model") or config.get("model_id")
    api_key = config.get("api_key")
    auth_ok = config.get("auth_ok")

    model_id = str(uuid.uuid4())

    new_config = {
        "models": {
            model_id: {
                "provider": provider,
                "model": model,
                "api_key": api_key,
                "auth_ok": auth_ok,
            }
        },
        "active_model_id": model_id,
    }

    save_config(new_config)
    return new_config


def get_active_model(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Return the active model entry from a registry config.
    Returns None if invalid or missing.
    """
    models = config.get("models")
    active_id = config.get("active_model_id")

    if not models or not active_id:
        return None

    return models.get(active_id)


def update_active_model(config: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a shallow patch to the active model entry and persist.
    """
    models = config.get("models")
    active_id = config.get("active_model_id")

    if not models or not active_id or active_id not in models:
        raise RuntimeError("Active model not found")

    models[active_id].update(patch)
    save_config(config)
    return config
