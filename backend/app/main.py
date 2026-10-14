from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.routes import chat, models, config, system, providers, history
from app.manifest.system import system_state
from app.routes.model_registry import router as model_registry_router
from app.security import LocalGuardMiddleware, get_allowed_origins, install_log_redaction

PROD = os.environ.get("PROJECT_X_ENV") == "production"
app = FastAPI(
    docs_url=None if PROD else "/docs",
    redoc_url=None if PROD else "/redoc",
    openapi_url=None if PROD else "/openapi.json",
)

# add_middleware: the LAST one added runs FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
    expose_headers=["X-Conversation-Id"],
)
app.add_middleware(LocalGuardMiddleware, allowed_origins=get_allowed_origins())

@app.on_event("startup")
def load_system_state():
    install_log_redaction()
    system_state.load()

# Routers (each included ONCE)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(config.router)
app.include_router(system.router)
app.include_router(providers.router)
app.include_router(model_registry_router)
app.include_router(history.router)

@app.get("/")
def health():
    return {"status": "ok"}
