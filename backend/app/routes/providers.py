from fastapi import APIRouter
from app.registry.providers import get_available_providers

router = APIRouter()

@router.get("/providers")
def list_providers():
    return get_available_providers()
