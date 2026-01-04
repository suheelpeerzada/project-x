from fastapi import APIRouter
from app.persistence.config_store import load_config
from app.schemas.system import SystemState

router = APIRouter()

@router.get("/status", response_model=SystemState)
def system_status():
    config = load_config()

    if not config:
        return SystemState(configured=False)

    return SystemState(
    configured=True,
    provider=config.get("provider"),
    model=config.get("model"),
    display_name=config.get("display_name"),
    auth_ok=config.get("auth_ok"),
    api_key_present=bool(config.get("api_key")),
    )

