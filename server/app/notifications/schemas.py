"""Notification request/response schemas (§22, §25, §62–63)."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.notifications import constants as c


class NotificationCreate(BaseModel):
    title: str | None = None
    message: str | None = None
    type: str = c.TYPE_TEXT
    priority: str = c.PRIORITY_NORMAL
    presentation: str = c.PRESENTATION_NORMAL

    routing: dict = Field(default_factory=dict)  # {mode, device_id?}
    voice: dict = Field(default_factory=dict)  # {source, language, provider, audio_id, ...}
    playback: dict = Field(default_factory=dict)  # {requested}
    content: dict = Field(default_factory=dict)  # {text} for voice (§25)
    actions: list = Field(default_factory=list)

    correlation_id: str | None = None
    thread_id: str | None = None
    group_key: str | None = None

    ttl_seconds: int | None = None
    expires_at: datetime | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    type: str
    priority: str
    title: str | None
    message: str | None
    voice: dict
    correlation_id: str | None
    thread_id: str | None
    group_key: str | None
    read_at: datetime | None
    expires_at: datetime
    created_at: datetime


class NotificationCreateOut(BaseModel):
    """Minimal agent-facing create response (§63)."""

    id: str
    status: str
    created_at: datetime
