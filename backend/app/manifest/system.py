from typing import Optional, Dict
from app.persistence.config_store import load_config


class SystemState:
    """
    Runtime system state.
    This is the single source of truth for whether the app is configured.
    """

    def __init__(self):
        self.configured: bool = False
        self.provider: Optional[str] = None
        self.model: Optional[str] = None
        self.api_key_present: bool = False
        self.auth_ok: bool | None = None

    def load(self) -> None:
        """
        Load configuration from disk into memory.
        Called once at backend startup.
        """
        config = load_config()

        if not config:
            self._reset()
            return

        self.provider = config.get("provider")
        self.model = config.get("model") or config.get("model_id")
        self.api_key_present = bool(config.get("api_key"))
        self.auth_ok = config.get("auth_ok")


        self.configured = bool(
            self.provider and
            self.model and
            self.api_key_present
        )

    def _reset(self) -> None:
        self.configured = False
        self.provider = None
        self.model = None
        self.api_key_present = False

    def as_dict(self):
        return {
        "configured": self.configured,
        "provider": self.provider,
        "model": self.model,
        "display_name": self.display_name(),
        "api_key_present": self.api_key_present,
        "auth_ok": self.auth_ok,
    }


    def display_name(self) -> str | None:
        if not self.provider or not self.model:
            return None

        provider_label = self.provider.capitalize()

        # Basic model prettifier (can be improved later)
        model_label = self.model.replace("-", " ").replace("_", " ")
        model_label = model_label.title()

        return f"{provider_label} · {model_label}"



# Singleton system state (imported everywhere)
system_state = SystemState()
