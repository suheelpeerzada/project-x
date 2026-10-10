from pydantic import BaseModel
from typing import Optional, Dict

class ModelMeta(BaseModel):
    size: Optional[str] = None
    quantization: Optional[str] = None

class ModelOut(BaseModel):
    id: str
    name: str
    meta: Optional[ModelMeta] = None
# -----------------------------
# Phase 2 Model Management
# -----------------------------

class AddModelRequest(BaseModel):
    provider: str
    model: str
    api_key: Optional[str] = None


class SwitchModelRequest(BaseModel):
    model_id: str