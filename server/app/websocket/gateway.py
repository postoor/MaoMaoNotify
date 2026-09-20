"""WebSocket gateway (§55): delivery, ACK, read sync.

Device authenticates with its device token via the ``token`` query parameter.
Inbound messages:
    {"type": "ack",  "notification_id": "...", "status": "delivered|displayed|played|opened"}
    {"type": "read", "notification_id": "..."}
    {"type": "ping"}
"""

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import authenticate_device
from app.core.errors import APIError
from app.db.base import get_session
from app.db.redis import get_redis
from app.models.device import Device
from app.models.notification import Notification
from app.notifications import constants as c
from app.notifications.delivery import apply_ack, mark_read
from app.notifications.responses import handle_response
from app.presence import manager as presence
from app.websocket.manager import manager

router = APIRouter()

_ACK_STATUSES = {
    c.DELIVERY_DELIVERED, c.DELIVERY_DISPLAYED, c.DELIVERY_PLAYED,
    c.DELIVERY_OPENED, c.DELIVERY_FAILED,
}


async def handle_message(session: AsyncSession, device: Device, msg: dict) -> None:
    mtype = msg.get("type")
    if mtype == "ack":
        nid = msg.get("notification_id")
        status = msg.get("status", c.DELIVERY_DELIVERED)
        if nid and status in _ACK_STATUSES:
            await apply_ack(session, device.id, nid, status)
    elif mtype == "read":
        nid = msg.get("notification_id")
        if nid:
            await mark_read(session, device.user_id, nid)
    elif mtype == "response":
        nid = msg.get("notification_id")
        action_id = msg.get("action_id")
        if not nid or not action_id:
            return
        notification = await session.get(Notification, nid)
        if notification is None or notification.user_id != device.user_id:
            return
        try:
            await handle_response(
                session, notification=notification, device_id=device.id,
                action_id=action_id, value=msg.get("value"),
            )
        except APIError as exc:
            await manager.send(
                device.id,
                {"event": "error", "code": exc.code, "notification_id": nid},
            )
    elif mtype == "ping":
        await manager.send(device.id, {"event": "pong"})


@router.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> None:
    try:
        device = await authenticate_device(session, token)
    except APIError:
        await websocket.close(code=1008)  # policy violation
        return

    await manager.connect(device.id, websocket, redis)
    await presence.mark_online(redis, device.user_id, device.id)  # connected ⟹ online
    try:
        while True:
            msg = await websocket.receive_json()
            await presence.refresh_online(redis, device.user_id, device.id)
            await handle_message(session, device, msg)
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(device.id, redis)
        await presence.mark_offline(redis, device.user_id, device.id)
