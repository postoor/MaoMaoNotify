"""Notification creation, idempotency, routing, and querying (§40, §46, §62)."""

from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.scopes import (
    NOTIFICATION_BROADCAST,
    NOTIFICATION_TARGET_DEVICE,
    has_scopes,
)
from app.core import redis_keys
from app.core.config import settings
from app.core.errors import APIError
from app.models.device import Device
from app.models.notification import Notification
from app.notifications import constants as c
from app.notifications.delivery import dispatch, schedule_fallback
from app.notifications.schemas import NotificationCreate
from app.presence import manager as presence
from app.routing.engine import plan_routes
from app.tts.synthesizer import VoiceSynthesizer


def _validate(body: NotificationCreate, mode: str) -> None:
    if body.type not in c.TYPES:
        raise APIError("invalid_request", f"Unknown type: {body.type}", 400)
    if body.priority not in c.PRIORITIES:
        raise APIError("invalid_request", f"Unknown priority: {body.priority}", 400)
    if body.presentation not in (c.PRESENTATION_NORMAL, c.PRESENTATION_SILENT):
        raise APIError("invalid_request", f"Unknown presentation: {body.presentation}", 400)
    if mode not in c.ROUTING_MODES:
        raise APIError("invalid_request", f"Unknown routing mode: {mode}", 400)
    if body.type == c.TYPE_VOICE and body.voice.get("source") not in c.VOICE_SOURCES:
        raise APIError("invalid_request", "voice.source is required for voice type.", 400)
    for action in body.actions:
        if not isinstance(action, dict) or not action.get("id"):
            raise APIError("invalid_request", "each action needs an id.", 400)
        if action.get("type") not in c.ACTION_TYPES:
            raise APIError("invalid_request", "action.type must be button or text_input.", 400)


def _check_scopes(mode: str, scopes: list[str]) -> None:
    if mode == c.ROUTE_ALL_DEVICES and not has_scopes(scopes, {NOTIFICATION_BROADCAST}):
        raise APIError("insufficient_scope", "all_devices requires notification:broadcast.", 403)
    if mode == c.ROUTE_SPECIFIC_DEVICE and not has_scopes(scopes, {NOTIFICATION_TARGET_DEVICE}):
        raise APIError(
            "insufficient_scope", "specific_device requires notification:target_device.", 403
        )


def _expiry(body: NotificationCreate) -> datetime:
    now = datetime.now(UTC)
    if body.expires_at is not None:
        return body.expires_at
    if body.ttl_seconds is not None:
        return now + timedelta(seconds=body.ttl_seconds)
    return now + timedelta(seconds=c.TTL_DEFAULTS[body.priority])


async def create_notification(
    session: AsyncSession,
    redis: Redis,
    *,
    user_id: str,
    agent_id: str | None,
    scopes: list[str],
    body: NotificationCreate,
    idempotency_key: str | None = None,
    synth: VoiceSynthesizer | None = None,
) -> Notification:
    mode = body.routing.get("mode", c.DEFAULT_ROUTING_MODE)
    _validate(body, mode)
    _check_scopes(mode, scopes)

    # Idempotency (§46): same agent + key returns the original notification.
    idem_redis_key = None
    if idempotency_key and agent_id:
        idem_redis_key = redis_keys.idempotency(agent_id, idempotency_key)
        existing_id = await redis.get(idem_redis_key)
        if existing_id:
            existing = await session.get(Notification, existing_id)
            if existing is not None:
                return existing

    specific_device = body.routing.get("device_id")
    if mode == c.ROUTE_SPECIFIC_DEVICE:
        dev = await session.get(Device, specific_device) if specific_device else None
        if dev is None or dev.user_id != user_id:
            raise APIError("invalid_request", "specific_device not found for user.", 400)

    notification = Notification(
        user_id=user_id,
        agent_id=agent_id,
        title=body.title,
        message=body.message if body.type == c.TYPE_TEXT else body.content.get("text"),
        type=body.type,
        priority=body.priority,
        presentation=body.presentation,
        routing_mode=mode,
        routing=body.routing,
        voice=body.voice,
        playback=body.playback,
        actions=body.actions,
        correlation_id=body.correlation_id,
        thread_id=body.thread_id,
        group_key=body.group_key,
        status=c.STATUS_QUEUED,
        expires_at=_expiry(body),
    )
    session.add(notification)
    await session.flush()

    # Voice sources (§25–34).
    if notification.type == c.TYPE_VOICE and synth is not None:
        source = notification.voice.get("source")
        if source == c.VOICE_SERVER_TTS:
            await synth.apply(session, notification, notification.message or "")
        elif source == c.VOICE_AGENT_AUDIO:
            await synth.attach_agent_audio(session, notification)

    ordered_active = await presence.ordered_device_ids(redis, user_id)
    all_devices = list(
        (await session.execute(select(Device.id).where(Device.user_id == user_id)))
        .scalars()
        .all()
    )
    plan = plan_routes(mode, body.priority, ordered_active, all_devices, specific_device)
    await dispatch(session, notification, plan)

    # ACK-timeout fallback (§53): if delivered to one device but more remain,
    # escalate to the next after the plan's timeout.
    if (
        settings.fallback_timer_enabled
        and mode == c.ROUTE_ACTIVE_WITH_FALLBACK
        and len(plan.targets) > 1
    ):
        schedule_fallback(notification.id, plan.timeout_seconds)

    if idem_redis_key:
        await redis.set(idem_redis_key, notification.id, ex=redis_keys.IDEMPOTENCY_TTL)

    return notification


async def list_notifications(
    session: AsyncSession, user_id: str, limit: int = 50
) -> list[Notification]:
    rows = (
        await session.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return list(rows)


async def get_notification(
    session: AsyncSession, user_id: str, notification_id: str
) -> Notification:
    n = await session.get(Notification, notification_id)
    if n is None or n.user_id != user_id:
        raise APIError("not_found", "Notification not found.", 404)
    return n
