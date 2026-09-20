"""Action responses: first-response-wins, action_resolved broadcast, webhooks
(§43, §44, §45, §65, §66)."""

from datetime import UTC, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import APIError
from app.models.agent import AgentWebhook
from app.models.notification import (
    Notification,
    NotificationDelivery,
    NotificationResponse,
)
from app.notifications import constants as c
from app.notifications.webhooks import send_event
from app.websocket.manager import manager


async def submit_response(
    session: AsyncSession,
    *,
    notification: Notification,
    device_id: str | None,
    action_id: str,
    value: str | None,
) -> NotificationResponse:
    """Record the response, enforcing first-response-wins (§44)."""
    action_ids = {a.get("id") for a in (notification.actions or [])}
    if action_id not in action_ids:
        raise APIError("unknown_action", f"Unknown action: {action_id}", 400)
    if notification.resolved_at is not None:
        raise APIError(
            "action_already_resolved", "This notification action was already resolved.", 409
        )

    response = NotificationResponse(
        notification_id=notification.id,
        device_id=device_id,
        action_id=action_id,
        value=value,
    )
    session.add(response)
    notification.resolved_at = datetime.now(UTC)
    notification.resolved_action_id = action_id
    notification.responded_by_device_id = device_id
    notification.status = c.STATUS_RESPONDED
    await session.commit()
    return response


async def _broadcast_resolved(
    session: AsyncSession, notification: Notification, action_id: str, exclude_device: str | None
) -> None:
    """Tell the user's other devices to disable the buttons (§44)."""
    rows = (
        await session.execute(
            select(NotificationDelivery.device_id).where(
                NotificationDelivery.notification_id == notification.id
            )
        )
    ).scalars().all()
    message = {
        "event": "action_resolved",
        "notification_id": notification.id,
        "action_id": action_id,
    }
    for device_id in set(rows):
        if device_id != exclude_device:
            await manager.send(device_id, message)


async def _notify_agent(session: AsyncSession, notification: Notification, response) -> None:
    if notification.agent_id is None:
        return
    webhooks = (
        await session.execute(
            select(AgentWebhook).where(AgentWebhook.agent_id == notification.agent_id)
        )
    ).scalars().all()
    await send_event(
        list(webhooks),
        c.EVENT_RESPONDED,
        {
            "notification_id": notification.id,
            "correlation_id": notification.correlation_id,
            "response": {"action_id": response.action_id, "value": response.value},
        },
    )


async def handle_response(
    session: AsyncSession,
    *,
    notification: Notification,
    device_id: str | None,
    action_id: str,
    value: str | None,
) -> NotificationResponse:
    response = await submit_response(
        session, notification=notification, device_id=device_id, action_id=action_id, value=value
    )
    await _broadcast_resolved(session, notification, action_id, exclude_device=device_id)
    try:
        await _notify_agent(session, notification, response)
    except httpx.HTTPError:
        pass  # webhook delivery is best-effort
    return response
