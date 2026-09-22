"""Notification endpoints: agent create (§62), user read/list (§61)."""

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthedAgent, get_current_device, get_current_user, require_scopes
from app.auth.scopes import NOTIFICATION_SEND
from app.core.config import settings
from app.core.errors import APIError
from app.core.runtime import effective_tts_provider
from app.db.base import get_session
from app.db.redis import get_redis
from app.models.device import Device
from app.models.notification import Notification
from app.models.user import User
from app.notifications.delivery import mark_read, signed_voice
from app.notifications.responses import handle_response
from app.notifications.schemas import (
    NotificationCreate,
    NotificationCreateOut,
    NotificationOut,
)
from app.notifications.service import create_notification, get_notification, list_notifications
from app.storage.base import StorageService
from app.storage.deps import get_storage
from app.tts.synthesizer import VoiceSynthesizer

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationCreateOut, status_code=201)
async def create(
    body: NotificationCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    authed: AuthedAgent = Depends(require_scopes(NOTIFICATION_SEND)),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
    storage: StorageService = Depends(get_storage),
) -> NotificationCreateOut:
    default_provider = await effective_tts_provider(session, settings)
    notification = await create_notification(
        session,
        redis,
        user_id=authed.agent.user_id,
        agent_id=authed.agent.id,
        scopes=authed.scopes,
        body=body,
        idempotency_key=idempotency_key,
        synth=VoiceSynthesizer(storage, settings, default_provider=default_provider),
    )
    return NotificationCreateOut(
        id=notification.id, status=notification.status, created_at=notification.created_at
    )


async def _to_out(
    n: Notification, session: AsyncSession, storage: StorageService
) -> NotificationOut:
    """Serialize a notification, minting a fresh signed audio_url (§35)."""
    out = NotificationOut.model_validate(n)
    out.voice = await signed_voice(n.voice, session, storage)
    return out


@router.get("", response_model=list[NotificationOut])
async def list_all(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
):
    notifications = await list_notifications(session, user.id)
    return [await _to_out(n, session, storage) for n in notifications]


@router.get("/{notification_id}", response_model=NotificationOut)
async def get_one(
    notification_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
):
    return await _to_out(await get_notification(session, user.id, notification_id), session, storage)


class ResponseIn(BaseModel):
    action_id: str
    value: str | None = None


class ResponseOut(BaseModel):
    id: str
    notification_id: str
    action_id: str
    value: str | None
    correlation_id: str | None


@router.post("/{notification_id}/responses", response_model=ResponseOut, status_code=201)
async def respond(
    notification_id: str,
    body: ResponseIn,
    device: Device = Depends(get_current_device),
    session: AsyncSession = Depends(get_session),
) -> ResponseOut:
    notification = await session.get(Notification, notification_id)
    if notification is None or notification.user_id != device.user_id:
        raise APIError("not_found", "Notification not found.", 404)
    response = await handle_response(
        session, notification=notification, device_id=device.id,
        action_id=body.action_id, value=body.value,
    )
    return ResponseOut(
        id=response.id, notification_id=notification.id, action_id=response.action_id,
        value=response.value, correlation_id=notification.correlation_id,
    )


@router.post("/{notification_id}/read", status_code=200)
async def read(
    notification_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    if not await mark_read(session, user.id, notification_id):
        raise APIError("not_found", "Notification not found.", 404)
    return {"status": "read"}
