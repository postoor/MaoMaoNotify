"""Aggregate router mounted at /api/v1."""

from fastapi import APIRouter

from app.api import (
    admin,
    agents,
    audio,
    auth,
    devices,
    me,
    notifications,
    preferences,
    presence,
)
from app.websocket import gateway

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(me.router)
api_router.include_router(devices.router)
api_router.include_router(agents.router)
api_router.include_router(preferences.router)
api_router.include_router(notifications.router)
api_router.include_router(audio.router)
api_router.include_router(presence.router)
api_router.include_router(admin.router)
api_router.include_router(gateway.router)  # /api/v1/ws
