from typing import List, Dict

def get_available_providers() -> List[Dict[str, str]]:
    return [
        {"id": "groq", "name": "Groq"},
        {"id": "openai", "name": "OpenAI"},
        {"id": "custom", "name": "Other / Local (custom endpoint)"},
    ]
