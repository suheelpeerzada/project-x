import json
from pathlib import Path
from typing import Optional, Dict, Any

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
    Merge partial updates into existing config.
    """
    config = load_config()
    if not config:
        raise RuntimeError("Config not initialized")

    config.update(patch)
    save_config(config)
    return config
