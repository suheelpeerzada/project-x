import json
from pathlib import Path
from typing import List, Dict

MODELS_PATH = Path.home() / ".project_x_models.json"

def load_user_models() -> List[Dict]:
    if not MODELS_PATH.exists():
        return []
    return json.loads(MODELS_PATH.read_text())

def save_user_models(models: List[Dict]):
    MODELS_PATH.write_text(json.dumps(models, indent=2))

def add_user_model(model: Dict):
    models = load_user_models()
    models.append(model)
    save_user_models(models)
