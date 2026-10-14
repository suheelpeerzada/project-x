import json
from pathlib import Path
from typing import Optional, Dict, Any
import uuid
import copy
import logging
import keyring
from keyring.errors import KeyringError

CONFIG_PATH = Path.home() / ".project_x_config.json"

log = logging.getLogger(__name__)
KEYRING_SERVICE = "project_x"


def _kr_set(model_id: str, key: str) -> bool:
    if keyring is None:
        return False
    try:
        keyring.set_password(KEYRING_SERVICE, model_id, key)
        return True
    except KeyringError:
        log.warning("No usable keychain; API key for %s stays in config file", model_id)
        return False


def _kr_get(model_id: str) -> Optional[str]:
    if keyring is None:
        return None
    try:
        return keyring.get_password(KEYRING_SERVICE, model_id)
    except KeyringError:
        return None


def _kr_delete(model_id: str) -> None:
    if keyring is None:
        return
    try:
        keyring.delete_password(KEYRING_SERVICE, model_id)
    except KeyringError:
        pass


def _stored_model_ids() -> set:
    try:
        return set((json.loads(CONFIG_PATH.read_text()).get("models") or {}).keys())
    except (OSError, ValueError):
        return set()


def load_config() -> Optional[Dict[str, Any]]:
    if not CONFIG_PATH.exists():
        return None
    config = json.loads(CONFIG_PATH.read_text())

    # Legacy single-model config → promote so the key can leave the file
    if "models" not in config or "active_model_id" not in config:
        if config.get("provider") and (config.get("model") or config.get("model_id")):
            return ensure_registry(config)
        return config

    needs_migration = False
    for mid, entry in (config.get("models") or {}).items():
        if entry.get("api_key"):
            needs_migration = True          # plaintext found in file
        else:
            key = _kr_get(mid)
            if key:
                entry["api_key"] = key      # hydrate in memory only
    if needs_migration:
        save_config(config)                 # moves keys into keychain
    return config


def save_config(data: Dict[str, Any]) -> None:
    previous_ids = _stored_model_ids()
    to_write = copy.deepcopy(data)          # never mutate caller's dict

    models = to_write.get("models") or {}
    for mid, entry in models.items():
        key = entry.get("api_key")
        if key and _kr_set(mid, key):
            entry.pop("api_key")            # safely in keychain
        elif not key:
            entry.pop("api_key", None)

    for mid in previous_ids - set(models.keys()):   # deleted models
        _kr_delete(mid)

    tmp = CONFIG_PATH.with_suffix(".tmp")           # atomic write
    tmp.write_text(json.dumps(to_write, indent=2))
    try:
        tmp.chmod(0o600)
    except OSError:
        pass
    tmp.replace(CONFIG_PATH)


def reset_config() -> None:
    for mid in _stored_model_ids():
        _kr_delete(mid)
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

# ----------------------------
# Phase 2 helpers (model management)
# ----------------------------

def get_model_by_provider_and_name(config: Dict[str, Any], provider: str, model: str, base_url=None):
    """
    Return (model_id, model_entry) if provider+model exists, else None.
    """
    models = config.get("models", {})
    for mid, entry in models.items():
        if (entry.get("provider") == provider
           and entry.get("model") == model
           and (entry.get("base_url") or None) == (base_url or None)):
            return mid, entry


def overwrite_model(config: Dict[str, Any], model_id: str, provider: str, model: str, api_key: str, base_url=None):
    """
    Overwrite an existing model entry but keep the same UUID.
    Reset auth_ok = False for first-time usage.
    """
    config["models"][model_id] = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "auth_ok": None,
    }
    if base_url: 
        config["models"][model_id]["base_url"] = base_url
    save_config(config)
    return model_id


def insert_new_model(config: Dict[str, Any], provider: str, model: str, api_key: str, base_url=None):
    """
    Create a new model entry with a fresh UUID and auth_ok=False.
    """
    new_id = str(uuid.uuid4())
    config.setdefault("models", {})
    config["models"][new_id] = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "auth_ok": None,
    }
    if base_url: 
        config["models"][new_id]["base_url"] = base_url
    save_config(config)
    return new_id


def switch_model(config: Dict[str, Any], model_id: str):
    """
    Switch active_model_id to an existing model.
    """
    if model_id not in config.get("models", {}):
        raise RuntimeError("Model ID not found")

    config["active_model_id"] = model_id
    save_config(config)
    return model_id