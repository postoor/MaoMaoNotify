"""Presence endpoints: device report (§12), user snapshot, agent view (§64)."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthedAgent, get_current_device, get_current_user, require_scopes
from app.auth.scopes import PRESENCE_READ
from app.db.base import get_session
from app.db.redis import get_redis
from app.models.device import Device
from app.models.user import User, UserPreferences
from app.presence import manager as presence
from app.presence.schemas import (
    AgentDeviceView,
    AgentPresenceView,
    Observation,
    PresenceSnapshot,
)

router = APIRouter(tags=["presence"])

_DESKTOP = {"macos", "linux"}


def _device_type(platform: str) -> str:
    if platform in _DESKTOP:
        return "desktop"
    if platform == "android":
        return "phone"
    return "unknown"


@router.post("/presence", status_code=200)
async def report_presence(
    obs: Observation,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> dict:
    await presence.record_observation(redis, device.user_id, device.id, obs)
    device.last_seen_at = datetime.now(UTC)
    await session.commit()
    return {"status": "ok"}


@router.get("/presence", response_model=PresenceSnapshot)
async def my_presence(
    user: User = Depends(get_current_user), redis: Redis = Depends(get_redis)
) -> PresenceSnapshot:
    return await presence.get_snapshot(redis, user.id)


@router.get("/agent/presence", response_model=AgentPresenceView)
async def agent_presence(
    authed: AuthedAgent = Depends(require_scopes(PRESENCE_READ)),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> AgentPresenceView:
    user_id = authed.agent.user_id
    snap = await presence.get_snapshot(redis, user_id)

    # Resolve device platforms for the type/platform view (no raw scores, §64).
    dev_ids = [snap.primary.device_id] if snap.primary else []
    dev_ids += [d.device_id for d in snap.secondary]
    platforms: dict[str, str] = {}
    if dev_ids:
        rows = (
            await session.execute(
                select(Device.id, Device.platform).where(Device.id.in_(dev_ids))
            )
        ).all()
        platforms = {r[0]: r[1] for r in rows}

    def view(dev_id: str, confidence: float) -> AgentDeviceView:
        platform = platforms.get(dev_id, "unknown")
        return AgentDeviceView(type=_device_type(platform), platform=platform, confidence=confidence)

    prefs = await session.get(UserPreferences, user_id)
    manual = prefs.manual_presence if prefs else "auto"
    if manual and manual != "auto":
        state = manual
    elif snap.primary is None:
        state = "offline"
    else:
        state = "active" if snap.primary.score >= 50 else "away"

    return AgentPresenceView(
        state=state,
        primary_device=view(snap.primary.device_id, snap.primary.confidence) if snap.primary else None,
        secondary_devices=[view(d.device_id, d.confidence) for d in snap.secondary],
    )
