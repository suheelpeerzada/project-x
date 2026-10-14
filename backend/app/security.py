"""
Local-API hardening for Project-X (stdlib only, apart from fastapi.HTTPException
used by the rate limiter).

  * LocalGuardMiddleware : Host allow-list (stops DNS rebinding) + Origin
                           allow-list (stops cross-site requests / CSRF)
  * RateLimiter          : tiny in-memory sliding window (FastAPI dependency)
  * install_log_redaction: masks API keys / bearer tokens in log output
  * validate_base_url    : SSRF guard for user-supplied provider URLs
"""
import ipaddress
import json
import logging
import os
import re
import socket
import threading
import time
from collections import deque
from typing import Iterable, Optional, Set
from urllib.parse import urlsplit

from fastapi import HTTPException

# ----------------------------
# Host / Origin guard
# ----------------------------

DEFAULT_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
# Vite dev server. Override with PROJECT_X_ORIGINS="http://localhost:3000,..."
DEFAULT_DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


def get_allowed_origins() -> list:
    raw = os.environ.get("PROJECT_X_ORIGINS", "")
    custom = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return custom or DEFAULT_DEV_ORIGINS


def _hostname(host_header: str) -> str:
    h = host_header.strip().lower()
    if h.startswith("["):                       # IPv6 literal: [::1]:8000
        return h.split("]")[0] + "]"
    return h.split(":")[0]


async def _deny(send, status: int, message: str) -> None:
    body = json.dumps({"detail": message}).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": body})


class LocalGuardMiddleware:
    """
    Pure-ASGI (safe with streaming responses).

    1. Host must be loopback            -> blocks DNS-rebinding attacks, where a
       hostile site resolves its own name to 127.0.0.1 to reach this server.
    2. If a browser sent an Origin, it must be allow-listed (or be this
       server's own origin, e.g. Swagger) -> blocks cross-site requests.
       Browsers always send Origin on cross-site POST/PATCH/DELETE, and a page
       cannot forge it. Requests with no Origin are non-browser clients (curl).
    """

    def __init__(self, app, allowed_origins: Iterable[str],
                 allowed_hosts: Iterable[str] = DEFAULT_HOSTS):
        self.app = app
        self.allowed_origins: Set[str] = {o.rstrip("/") for o in allowed_origins}
        self.allowed_hosts: Set[str] = set(allowed_hosts)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        h = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
        host_header = h.get("host", "")

        if _hostname(host_header) not in self.allowed_hosts:
            return await _deny(send, 403, "Host not allowed")

        origin = h.get("origin")
        if origin is not None:
            origin = origin.rstrip("/")
            own = f"http://{host_header}".rstrip("/")
            if origin != own and origin not in self.allowed_origins:
                return await _deny(send, 403, "Origin not allowed")

        return await self.app(scope, receive, send)


# ----------------------------
# Rate limiting
# ----------------------------

class RateLimiter:
    """
    Sliding-window limiter, usable as `dependencies=[Depends(limiter)]`.
    Single-user app, so one window per endpoint group (no per-IP keys).
    Protects the user's provider quota from runaway loops or abusive callers.
    """

    def __init__(self, name: str, max_calls: int, per_seconds: int):
        self.name, self.max_calls, self.window = name, max_calls, per_seconds
        self._hits: deque = deque()
        self._lock = threading.Lock()

    def __call__(self) -> None:
        now = time.monotonic()
        with self._lock:
            while self._hits and now - self._hits[0] > self.window:
                self._hits.popleft()
            if len(self._hits) >= self.max_calls:
                retry = max(1, int(self.window - (now - self._hits[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many {self.name} requests. Try again in {retry}s.",
                    headers={"Retry-After": str(retry)},
                )
            self._hits.append(now)


chat_limiter = RateLimiter("chat", 30, 60)
upload_limiter = RateLimiter("upload", 20, 60)
provider_limiter = RateLimiter("provider lookup", 20, 60)
config_limiter = RateLimiter("config", 30, 60)


# ----------------------------
# Log redaction
# ----------------------------

_SECRET_PATTERNS = [
    re.compile(r"\b(?:gsk|sk|hf|xai|cc)[_-][A-Za-z0-9_\-]{16,}"),   # provider key shapes
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{8,}"),
    re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[A-Za-z0-9._\-]{8,}"),
]


def redact(text: str) -> str:
    text = _SECRET_PATTERNS[0].sub("[REDACTED]", text)
    text = _SECRET_PATTERNS[1].sub("Bearer [REDACTED]", text)
    text = _SECRET_PATTERNS[2].sub(r"\1[REDACTED]", text)
    return text


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Redact the message and each string argument but KEEP the args shape:
        # uvicorn's access formatter unpacks exactly 5 args.
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if isinstance(record.args, tuple):
                record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
            elif isinstance(record.args, dict):
                record.args = {k: redact(v) if isinstance(v, str) else v for k, v in record.args.items()}
        except Exception:
            pass
        return True


def install_log_redaction() -> None:
    """Call once at startup (after uvicorn has configured logging)."""
    flt = _RedactFilter()
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
        for handler in logging.getLogger(name).handlers:
            handler.addFilter(flt)


# ----------------------------
# SSRF guard for user-supplied provider URLs (Phase 2B: custom OpenAI / Ollama)
# ----------------------------

def validate_base_url(url: str, allow_loopback: bool = True) -> str:
    """
    Raises ValueError for URLs the backend must never call:
    non-http(s), credentials in the URL, link-local / cloud-metadata
    addresses (169.254.x.x), multicast/reserved ranges, and plain http to a
    public host (the API key would travel in clear text).
    Loopback (Ollama) and private LAN addresses are allowed.
    Call this again right before every request (DNS can change), and make the
    request with allow_redirects=False.
    """
    parts = urlsplit((url or "").strip())
    if parts.scheme not in ("http", "https"):
        raise ValueError("URL must start with http:// or https://")
    if not parts.hostname:
        raise ValueError("URL has no host")
    if parts.username or parts.password:
        raise ValueError("Credentials inside URLs are not allowed")

    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parts.hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError("Could not resolve that host")

    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0].split("%")[0])
        except ValueError:
            raise ValueError("Unrecognised address")
        if ip.version == 6 and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if ip.is_link_local or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise ValueError("That address is not allowed")
        if ip.is_loopback and not allow_loopback:
            raise ValueError("Loopback addresses are not allowed here")
        if parts.scheme == "http" and not (ip.is_loopback or ip.is_private):
            raise ValueError("Use https:// for hosts on the public internet")
    return url.strip().rstrip("/")
