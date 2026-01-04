from pydantic import BaseModel
from typing import Optional, Dict

class ModelMeta(BaseModel):
    size: Optional[str] = None
    quantization: Optional[str] = None

class ModelOut(BaseModel):
    id: str
    name: str
    meta: Optional[ModelMeta] = None
