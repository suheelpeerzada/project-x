from pydantic import BaseModel
from typing import Optional


class SystemState(BaseModel):
    configured: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    display_name: Optional[str] = None
    auth_ok: Optional[bool] = None
    api_key_present: Optional[bool] = None  # ← ADD
