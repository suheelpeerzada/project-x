import requests
from fastapi import HTTPException


# ---- Provider endpoints ----

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
HF_CHAT_URL = "https://api-inference.huggingface.co/models"


# ---- Main dispatcher ----

def call_llm(
    provider: str,
    model: str,
    api_key: str | None,
    message: str,
) -> str:
    if provider == "groq":
        return _call_groq(model, api_key, message)

    if provider == "openai":
        return _call_openai(model, api_key, message)

    if provider == "huggingface":
        return _call_huggingface(model, api_key, message)

    if provider == "local":
        return _call_local(model, message)

    raise HTTPException(
        status_code=400,
        detail=f"Unsupported provider: {provider}"
    )


# ---- Providers ----

def _call_groq(model: str, api_key: str | None, message: str) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing Groq API key")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(GROQ_CHAT_URL, json=payload, headers=headers, timeout=30)

    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid Groq API key")

    if not r.ok:
        raise HTTPException(
            status_code=502,
            detail=f"Groq error: {r.text}"
        )

    data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_openai(model: str, api_key: str | None, message: str) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing OpenAI API key")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    r = requests.post(OPENAI_CHAT_URL, json=payload, headers=headers, timeout=30)

    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid OpenAI API key")

    if not r.ok:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI error: {r.text}"
        )

    data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_huggingface(model: str, api_key: str | None, message: str) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing HuggingFace API key")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "inputs": message,
    }

    r = requests.post(
        f"{HF_CHAT_URL}/{model}",
        json=payload,
        headers=headers,
        timeout=30,
    )

    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid HuggingFace API key")

    if not r.ok:
        raise HTTPException(
            status_code=502,
            detail=f"HuggingFace error: {r.text}"
        )

    data = r.json()

    # HF responses vary by model
    if isinstance(data, list) and "generated_text" in data[0]:
        return data[0]["generated_text"]

    raise HTTPException(
        status_code=502,
        detail="Unexpected HuggingFace response format"
    )


def _call_local(model: str, message: str) -> str:
    """
    Placeholder for Ollama / local engines.
    No API key.
    """
    raise HTTPException(
        status_code=501,
        detail="Local provider not implemented yet"
    )
