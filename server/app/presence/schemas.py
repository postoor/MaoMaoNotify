"""Presence observation and output schemas (§12, §17, §64).

The client reports *observations only* — it never declares "I am active" (§12).
Privacy: no keystrokes, coordinates, URLs, or raw sensor streams (§13).
"""

from datetime import datetime

from pydantic import BaseModel, Field


class Observation(BaseModel):
    screen: str | None = None  # "on" | "off"
    locked: bool | None = None
    last_interaction_ms: int | None = None
    app_state: str | None = None  # "foreground" | "background"
    motion: str | None = None  # stationary | moving | handheld | walking | unknown (§15)
    audio: dict = Field(default_factory=dict)
    battery: dict = Field(default_factory=dict)
    timestamp: datetime | None = None


class ActiveDeviceOut(BaseModel):
    device_id: str
    score: int
    confidence: float


class PresenceSnapshot(BaseModel):
    """User-facing presence (§17): full scores allowed here."""

    primary: ActiveDeviceOut | None = None
    secondary: list[ActiveDeviceOut] = Field(default_factory=list)


class AgentDeviceView(BaseModel):
    """Agent-facing device view (§64): type/platform/confidence, no raw score."""

    type: str  # desktop | phone
    platform: str
    confidence: float


class AgentPresenceView(BaseModel):
    state: str  # active | available | busy | away | do_not_disturb | offline
    primary_device: AgentDeviceView | None = None
    secondary_devices: list[AgentDeviceView] = Field(default_factory=list)
