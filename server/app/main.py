"""MaoMaoNotify backend entrypoint.

Phase 1: auth, multi-user, device registry, agent registry. Presence, routing,
notifications, TTS, and the WebSocket gateway arrive in later phases.
"""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.errors import register_error_handlers
from app.core.ids import new_id
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="MaoMaoNotify", version="0.1.0")


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = new_id("req")
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


register_error_handlers(app)
app.include_router(api_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


# Web Admin (§70) — static SPA served at /admin when present.
# WEB_ADMIN_DIR overrides the location (set in the production image).
_WEB_DIR = Path(os.environ.get("WEB_ADMIN_DIR") or (Path(__file__).resolve().parents[2] / "web"))
if (_WEB_DIR / "index.html").exists():
    app.mount("/admin", StaticFiles(directory=str(_WEB_DIR), html=True), name="admin")
