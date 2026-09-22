"""Delivery orchestration and lifecycle (§49, §50, §53).

- ``dispatch`` fans out a notification to its routed devices, pushing to online
  devices via WebSocket. For active modes it targets the first *online* device
  (availability fallback, §53); for all_devices / specific_device it pushes to
  every online target.
- ``run_fallback`` implements ACK-timeout escalation: if the sent device has
  not acknowledged, cancel it and push to the next online candidate. (Wiring
  this to a timer/scheduler is a runtime concern; the logic is unit-tested.)
- ``apply_ack`` / ``mark_read`` advance delivery and notification state.
"""

import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.audio import AudioAsset
from app.models.device import Device
from app.models.notification import Notification, NotificationDelivery
from app.notifications import constants as c
from app.routing.engine import RoutingPlan
from app.storage.base import StorageService
from app.websocket.manager import manager

log = get_logger("delivery")

_ACK_TIMESTAMP = {
    c.DELIVERY_DELIVERED: "delivered_at",
    c.DELIVERY_DISPLAYED: "displayed_at",
    c.DELIVERY_PLAYED: "played_at",
    c.DELIVERY_OPENED: "opened_at",
    c.DELIVERY_FAILED: "failed_at",
}


def _now() -> datetime:
    return datetime.now(UTC)


async def signed_voice(
    voice: dict | None,
    session: AsyncSession,
    storage: StorageService | None,
) -> dict:
    """Return a copy of ``voice`` with a freshly-signed ``audio_url`` minted from
    its ``audio_id`` (§35).

    The URL is short-lived (``AUDIO_URL_TTL_SECONDS``) and is never persisted, so
    every serialization hands the client a currently-valid URL. A no-op when the
    payload has no audio asset (client_tts / plain text) or no storage is given.
    """
    voice = dict(voice or {})
    audio_id = voice.get("audio_id")
    if not audio_id or storage is None:
        return voice
    asset = await session.get(AudioAsset, audio_id)
    if asset is None or not asset.storage_key:
        return voice
    voice["audio_url"] = await storage.signed_url(
        asset.storage_key, settings.audio_url_ttl_seconds
    )
    return voice


async def ws_payload(
    n: Notification, session: AsyncSession, storage: StorageService | None = None
) -> dict:
    return {
        "event": "notification",
        "notification": {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "message": n.message,
            "priority": n.priority,
            "presentation": n.presentation,
            "voice": await signed_voice(n.voice, session, storage),
            "playback": n.playback,
            "actions": n.actions,
            "correlation_id": n.correlation_id,
            "thread_id": n.thread_id,
            "group_key": n.group_key,
            "expires_at": n.expires_at.isoformat() if n.expires_at else None,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        },
    }


def _mark_sent(delivery: NotificationDelivery) -> None:
    delivery.status = c.DELIVERY_SENT
    delivery.sent_at = _now()


async def dispatch(
    session: AsyncSession,
    notification: Notification,
    plan: RoutingPlan,
    storage: StorageService | None = None,
) -> list[NotificationDelivery]:
    deliveries: list[NotificationDelivery] = []
    for i, dev in enumerate(plan.targets):
        d = NotificationDelivery(
            notification_id=notification.id,
            device_id=dev,
            status=c.DELIVERY_ROUTED,
            order_index=i,
        )
        session.add(d)
        deliveries.append(d)
    await session.flush()

    payload = await ws_payload(notification, session, storage)
    multi = plan.mode in (c.ROUTE_ALL_DEVICES, c.ROUTE_SPECIFIC_DEVICE)
    sent_any = False

    for d in deliveries:
        if not manager.is_online(d.device_id):
            continue
        await manager.send(d.device_id, payload)
        _mark_sent(d)
        sent_any = True
        if not multi:
            break  # active modes: first online device only

    notification.status = c.STATUS_SENT if sent_any else c.STATUS_ROUTED
    await session.commit()
    await send_push_wakes(session, notification, deliveries)
    return deliveries


async def send_push_wakes(
    session: AsyncSession,
    notification: Notification,
    deliveries: list[NotificationDelivery],
    *,
    transport: httpx.BaseTransport | None = None,
) -> int:
    """Wake offline Android devices via their UnifiedPush endpoint (§56 alt).

    The endpoint (self-hosted ntfy distributor) delivers this POST body to the
    app's UnifiedPush receiver, which then fetches the notification. Best-effort.
    Returns the number of wake messages sent.
    """
    offline_ids = [
        d.device_id for d in deliveries
        if d.status == c.DELIVERY_ROUTED and not manager.is_online(d.device_id)
    ]
    if not offline_ids:
        return 0
    devices = (
        await session.execute(select(Device).where(Device.id.in_(offline_ids)))
    ).scalars().all()
    targets = [d for d in devices if d.platform == "android" and d.push_endpoint]
    if not targets:
        return 0

    body = json.dumps({"type": "wake", "notification_id": notification.id}).encode()
    sent = 0
    async with httpx.AsyncClient(transport=transport, timeout=5.0) as client:
        for dev in targets:
            try:
                await client.post(
                    dev.push_endpoint,
                    content=body,
                    headers={"Content-Type": "application/json", "Title": "MaoMaoNotify"},
                )
                sent += 1
            except httpx.HTTPError:
                log.warning("push wake failed", extra={"device_id": dev.id})
    return sent


async def run_fallback(
    session: AsyncSession, notification_id: str, storage: StorageService | None = None
) -> bool:
    """Escalate if the currently-sent device hasn't acknowledged delivery.

    Returns True if a fallback push was made. Intended to run after the plan's
    ``timeout_seconds``.
    """
    rows = (
        await session.execute(
            select(NotificationDelivery)
            .where(NotificationDelivery.notification_id == notification_id)
            .order_by(NotificationDelivery.order_index)
        )
    ).scalars().all()

    acked = {c.DELIVERY_DELIVERED, c.DELIVERY_DISPLAYED, c.DELIVERY_PLAYED, c.DELIVERY_OPENED}
    if any(d.status in acked for d in rows):
        return False  # already delivered somewhere

    sent = next((d for d in rows if d.status == c.DELIVERY_SENT), None)
    if sent is None:
        return False

    nxt = next(
        (d for d in rows
         if d.order_index > sent.order_index
         and d.status == c.DELIVERY_ROUTED
         and manager.is_online(d.device_id)),
        None,
    )
    if nxt is None:
        return False

    sent.status = c.DELIVERY_FALLBACK_CANCELLED
    notification = await session.get(Notification, notification_id)
    await manager.send(nxt.device_id, await ws_payload(notification, session, storage))
    _mark_sent(nxt)
    await session.commit()
    return True


async def _delayed_fallback(
    notification_id: str, delay: float, session_factory: Callable
) -> None:
    try:
        await asyncio.sleep(delay)
        from app.storage.deps import get_storage

        storage = await get_storage()
        async with session_factory() as session:
            await run_fallback(session, notification_id, storage)
    except Exception:  # noqa: BLE001 — a fallback timer must never crash the loop
        log.warning("fallback timer failed", extra={"notification_id": notification_id})


def schedule_fallback(
    notification_id: str, delay: float, session_factory: Callable | None = None
) -> asyncio.Task:
    """Escalate delivery after `delay` seconds if unacknowledged (§53).

    Runs in the background with its own DB session (the request session is gone
    by the time it fires). ``session_factory`` is injectable for tests.
    """
    if session_factory is None:
        from app.db.base import SessionLocal

        session_factory = SessionLocal
    return asyncio.create_task(_delayed_fallback(notification_id, delay, session_factory))


async def apply_ack(
    session: AsyncSession, device_id: str, notification_id: str, status: str
) -> None:
    delivery = (
        await session.execute(
            select(NotificationDelivery).where(
                NotificationDelivery.notification_id == notification_id,
                NotificationDelivery.device_id == device_id,
            )
        )
    ).scalar_one_or_none()
    if delivery is None:
        return
    delivery.status = status
    ts_field = _ACK_TIMESTAMP.get(status)
    if ts_field:
        setattr(delivery, ts_field, _now())
    notification = await session.get(Notification, notification_id)
    if notification is not None and status in _ACK_TIMESTAMP and status != c.DELIVERY_FAILED:
        notification.status = status  # advance user-facing status
    await session.commit()


async def mark_read(session: AsyncSession, user_id: str, notification_id: str) -> bool:
    """Mark read at the user level (§51). Idempotent; returns False if not owned."""
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != user_id:
        return False
    if notification.read_at is None:
        notification.read_at = _now()
        await session.commit()
    return True
