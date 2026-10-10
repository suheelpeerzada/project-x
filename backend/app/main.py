from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import chat, models, config, system, providers, history
from app.manifest.system import system_state
from app.routes.model_registry import router as model_registry_router

app = FastAPI()

# Routers (each included ONCE)
app.include_router(chat.router)
app.include_router(models.router)
app.include_router(config.router)
app.include_router(system.router)
app.include_router(providers.router)
app.include_router(model_registry_router)
app.include_router(history.router)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)

@app.on_event("startup")
def load_system_state():
    system_state.load()
    print(system_state.as_dict())

@app.get("/")
def health():
    return {"status": "ok"}
