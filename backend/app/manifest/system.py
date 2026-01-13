from typing import Optional, Dict, Any
from app.persistence.config_store import load_config
import uuid


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

        # Phase 1 additions (internal only)
        self._active_model_id: Optional[str] = None
        self._models: Dict[str, Dict[str, Any]] = {}

    def load(self) -> None:
        """
        Load configuration from disk into memory.
        Called once at backend startup.
        Supports both legacy single-model config
        and new multi-model registry config.
        """
        config = load_config()

        if not config:
            self._reset()
            return

        # --- Case 1: New multi-model registry ---
        if "models" in config and "active_model_id" in config:
            models = config.get("models") or {}
            active_id = config.get("active_model_id")

            active_model = models.get(active_id)

            if not active_model:
                # Invalid registry state → treat as unconfigured
                self._reset()
                return

            self._models = models
            self._active_model_id = active_id

            self._apply_active_model(active_model)
            return

        # --- Case 2: Legacy single-model config (backward compatibility) ---
        provider = config.get("provider")
        model = config.get("model") or config.get("model_id")
        api_key = config.get("api_key")
        auth_ok = config.get("auth_ok")

        if not (provider and model):
            self._reset()
            return

        # Create an in-memory implicit registry (NOT persisted)
        implicit_id = "legacy"

        self._models = {
            implicit_id: {
                "provider": provider,
                "model": model,
                "api_key": api_key,
                "auth_ok": auth_ok,
            }
        }
        self._active_model_id = implicit_id

        self._apply_active_model(self._models[implicit_id])

    def _apply_active_model(self, model_entry: Dict[str, Any]) -> None:
        """
        Populate public runtime fields from an active model entry.
        """
        self.provider = model_entry.get("provider")
        self.model = model_entry.get("model")
        self.api_key_present = bool(model_entry.get("api_key"))
        self.auth_ok = model_entry.get("auth_ok")

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
        self.auth_ok = None
        self._active_model_id = None
        self._models = {}

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

        model_label = self.model.replace("-", " ").replace("_", " ")
        model_label = model_label.title()

        return f"{provider_label} · {model_label}"


# Singleton system state (imported everywhere)
system_state = SystemState()
