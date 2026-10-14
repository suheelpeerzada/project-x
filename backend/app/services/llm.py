import requests
from fastapi import HTTPException
import json
from app.security import validate_base_url


# ---- Provider endpoints ----

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
HF_CHAT_URL = "https://api-inference.huggingface.co/models"

GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"
OPENAI_MODELS_URL = "https://api.openai.com/v1/models"
HF_WHOAMI_URL = "https://huggingface.co/api/whoami-v2"

_AUTH_CHECK_URLS = {
    "groq": GROQ_MODELS_URL,
    "openai": OPENAI_MODELS_URL,
    "huggingface": HF_WHOAMI_URL,
}
CUSTOM = "custom-openai"

def _custom_url(base_url, path: str) -> str:
    if not base_url:
        raise HTTPException(status_code=400, detail="This model needs a base URL")
    try:
        root = validate_base_url(base_url)      # SSRF guard, re-checked on every call
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid base URL: {e}")
    return f"{root}{path}"

def _headers(api_key) -> dict:
    h = {"Content-Type": "application/json"}
    if api_key:                                  # local servers usually need no key
        h["Authorization"] = f"Bearer {api_key}"
    return h

def _server_message(r) -> str:
    try:
        err = r.json().get("error")
        msg = err.get("message") if isinstance(err, dict) else err
        return str(msg or "")[:200]
    except Exception:
        return ""

def _raise_for_custom(r, model: str) -> None:
    if r.ok:
        return
    if r.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="The endpoint rejected your API key")
    if r.status_code in (400, 404, 422):
        said = _server_message(r)
        raise HTTPException(
            status_code=404,
            detail=f"The endpoint could not use model '{model}'"
                   + (f" (it said: {said})" if said else "")
                   + ". Check the model name and base URL.",
        )
    raise HTTPException(status_code=502, detail=f"Endpoint error: HTTP {r.status_code}")

MAX_REPLY_TOKENS = 4096        # hard cap per reply (hidden reasoning counts too)
INPUT_CHAR_BUDGET = 14000      # ≈3.5K tokens of history per request (see note below)

_ANSWER_WORDS = int(round(MAX_REPLY_TOKENS * 0.75 * 0.5, -2))   # ≈1,500 words

SYSTEM_PROMPT = (
    f"Each of your replies is hard-capped at about {MAX_REPLY_TOKENS} tokens, "
    "and hidden reasoning counts toward that cap, so keep the visible answer "
    f"under roughly {_ANSWER_WORDS} words. "
    "If the complete answer would not fit, write the part that fits, stop at a "
    "natural break such as the end of a section, and make your final sentence a "
    "question asking whether the user would like you to continue "
    "(for example: \"Would you like me to continue with the next section?\"). "
    "If the answer fits, give it in full and do not ask. "
    "Format replies in Markdown. Write math with $...$ inline and $$...$$ for "
    "display equations, never \\( \\) or \\[ \\]."
)

LENGTH_NOTICE = '\n\n*— Reply hit the length limit. Say "continue" to pick up where it stopped.*'


def _trim_history(messages: list[dict], budget: int = INPUT_CHAR_BUDGET) -> list[dict]:
    """Keep the most recent messages that fit the budget (always keeps the last one)."""
    kept, used = [], 0
    for m in reversed(messages):
        used += len(m["content"])
        if kept and used > budget:
            break
        kept.append(m)
    return list(reversed(kept))


def check_auth(provider: str, api_key: str | None) -> None:
    """Cheap key check. 401 = bad key; anything else = could not verify."""
    if provider == "local":
        raise HTTPException(status_code=501, detail="Local provider not implemented yet")

    url = _AUTH_CHECK_URLS.get(provider)
    if not url:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not api_key:
        raise HTTPException(status_code=401, detail=f"Missing {provider} API key")

    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=15, allow_redirects=False)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Could not reach {provider}: {type(e).__name__}")

    if r.status_code == 401:
        raise HTTPException(status_code=401, detail=f"Invalid {provider} API key")
    if not r.ok:
        raise HTTPException(status_code=502, detail=f"{provider} error: HTTP {r.status_code}")
    
# ---- Main dispatcher ----

def call_llm(provider: str, model: str, api_key: str | None, message: str, base_url: str | None = None) -> str:
    try:
        if provider == "groq":
            return _call_groq(model, api_key, message)
        if provider == "openai":
            return _call_openai(model, api_key, message)
        if provider == "huggingface":
            return _call_huggingface(model, api_key, message)
        if provider == "local":
            return _call_local(model, message)
        if provider == CUSTOM: 
            return _call_custom(model, api_key, message, base_url)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Network error: {type(e).__name__}")

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")

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
    
    if r.status_code == 404 or "model_not_found" in r.text:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model}' is no longer available on Groq. Pick another model.",
        )

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

    if r.status_code == 404 or "model_not_found" in r.text:
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model}' is no longer available on OpenAI. Pick another model.",
        )

    if not r.ok:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI error: {r.text}"
        )

    data = r.json()
    return data["choices"][0]["message"]["content"]

def _call_custom(model: str, api_key: str | None, message: str, base_url: str | None) -> str:
    r = requests.post(
        _custom_url(base_url, "/chat/completions"),
        json={"model": model, "messages": [{"role": "user", "content": message}]},
        headers=_headers(api_key), timeout=30, allow_redirects=False,
    )
    _raise_for_custom(r, model)
    return r.json()["choices"][0]["message"]["content"]

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

_OPENAI_COMPAT_MODELS = {
    "groq": "https://api.groq.com/openai/v1/models",
    "openai": "https://api.openai.com/v1/models",
}
_NON_CHAT = ("whisper", "tts", "guard", "embed", "moderation",
             "dall-e", "image", "transcribe", "safeguard")


def list_models(provider: str, api_key: str | None) -> list[dict]:
    """Live list of chat models the key can actually use right now."""
    url = _OPENAI_COMPAT_MODELS.get(provider)
    if not url:
        raise HTTPException(status_code=400, detail=f"Live model list not supported for {provider}")
    if not api_key:
        raise HTTPException(status_code=401, detail=f"Missing {provider} API key")
    try:
        r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=15,allow_redirects=False)
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Could not reach {provider}: {type(e).__name__}")
    if r.status_code == 401:
        raise HTTPException(status_code=401, detail=f"Invalid {provider} API key")
    if not r.ok:
        raise HTTPException(status_code=502, detail=f"{provider} error: HTTP {r.status_code}")

    out = []
    for m in r.json().get("data", []):
        mid = m.get("id", "")
        if m.get("active") is False:
            continue
        if any(x in mid.lower() for x in _NON_CHAT):
            continue
        out.append({"id": mid, "owned_by": m.get("owned_by")})
    return sorted(out, key=lambda m: m["id"])


def verify_model(provider: str, model: str, api_key: str | None, base_url: str | None = None) -> None:
    """401 = bad key. 404 = key fine but model gone. Others = couldn't verify."""
    if provider == CUSTOM:
        # /models is not universal, so verify with one tiny real request.
        try:
            r = requests.post(
                _custom_url(base_url, "/chat/completions"),
                json={"model": model, "messages": [{"role": "user", "content": "Reply with OK."}]},
                headers=_headers(api_key), timeout=30, allow_redirects=False,
            )
        except requests.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Could not reach the endpoint: {type(e).__name__}")
        _raise_for_custom(r, model)
        return
    if provider in _OPENAI_COMPAT_MODELS:
        ids = {m["id"] for m in list_models(provider, api_key)}
        if model not in ids:
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model}' is no longer available on {provider}. Pick another model.",
            )
        return
    check_auth(provider, api_key)

_STREAM_URLS = {"groq": GROQ_CHAT_URL, "openai": OPENAI_CHAT_URL}


def stream_llm(provider: str, model: str, api_key: str | None, messages: list[dict], base_url: str | None = None):
    """Returns an iterator of text chunks. Errors before the first token raise HTTPException."""
    if provider == CUSTOM:
        url = _custom_url(base_url, "/chat/completions")
    else:
        url = _STREAM_URLS.get(provider)
    if not url:
        raise HTTPException(status_code=501, detail=f"Streaming not supported for {provider}")
    if not api_key and provider != CUSTOM:
        raise HTTPException(status_code=401, detail=f"Missing {provider} API key")

    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + _trim_history(messages),
        "stream": True,
        ("max_tokens" if provider == CUSTOM else "max_completion_tokens"): MAX_REPLY_TOKENS,
    }

    try:
        r = requests.post(
            url,
            json=payload,
            headers=_headers(api_key),
            stream=True,
            timeout=(10, 60),
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Network error: {type(e).__name__}")

    if provider == CUSTOM:
        try:
            _raise_for_custom(r, model)
        finally:
            if not r.ok:
                r.close()
    else:
        if r.status_code == 401:
            r.close()
            raise HTTPException(status_code=401, detail=f"Invalid {provider} API key")
        if r.status_code == 404 or "model_not_found" in (r.text if not r.ok else ""):
            r.close()
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model}' is no longer available on {provider}. Pick another model.",
            )
        if not r.ok:
            detail = f"{provider} error: HTTP {r.status_code}"
            r.close()
            raise HTTPException(status_code=502, detail=detail)

    def gen():
        try:
            for raw in r.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8")
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                choice = (chunk.get("choices") or [{}])[0]
                text = choice.get("delta", {}).get("content")
                if text:
                    yield text
                if choice.get("finish_reason") == "length":
                    yield LENGTH_NOTICE      # model was cut off despite the prompt
        finally:
            r.close()

    return gen()