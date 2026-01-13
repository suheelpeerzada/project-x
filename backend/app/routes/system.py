from fastapi import APIRouter
from app.manifest.system import system_state
from app.schemas.system import SystemState

router = APIRouter()

@router.get("/status", response_model=SystemState)
def system_status():
    return SystemState(**system_state.as_dict())