"""Audio asset access (§61). Returns a short-lived signed URL (§35).

Phase 5 exposes reads for server-TTS output; agent uploads land in Phase 6.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import AuthedAgent, get_current_user, require_scopes
from app.auth.scopes import NOTIFICATION_SEND
from app.core.config import settings
from app.core.errors import APIError
from app.db.base import get_session
from app.models.audio import AudioAsset
from app.models.user import User
from app.storage.base import StorageService
from app.storage.deps import get_storage
from app.tts.base import extension_for

router = APIRouter(prefix="/audio", tags=["audio"])


class AudioOut(BaseModel):
    id: str
    url: str
    content_type: str


class UploadRequest(BaseModel):
    content_type: str = "audio/mpeg"


class UploadOut(BaseModel):
    audio_id: str
    upload_url: str
    method: str = "PUT"
    headers: dict
    expires_in: int


@router.post("/uploads", response_model=UploadOut, status_code=201)
async def request_upload(
    body: UploadRequest,
    authed: AuthedAgent = Depends(require_scopes(NOTIFICATION_SEND)),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> UploadOut:
    asset = AudioAsset(
        user_id=authed.agent.user_id,
        source="agent_audio",
        provider=None,
        content_type=body.content_type,
        size=0,
        storage_key="",
    )
    session.add(asset)
    await session.flush()
    asset.storage_key = f"audio/{asset.id}.{extension_for(body.content_type)}"
    await session.commit()

    ttl = settings.audio_url_ttl_seconds
    url = await storage.presigned_put_url(asset.storage_key, body.content_type, ttl)
    return UploadOut(
        audio_id=asset.id,
        upload_url=url,
        headers={"Content-Type": body.content_type},
        expires_in=ttl,
    )


@router.get("/{audio_id}", response_model=AudioOut)
async def get_audio(
    audio_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    storage: StorageService = Depends(get_storage),
) -> AudioOut:
    asset = await session.get(AudioAsset, audio_id)
    if asset is None or asset.user_id != user.id:
        raise APIError("not_found", "Audio asset not found.", 404)
    url = await storage.signed_url(asset.storage_key, settings.audio_url_ttl_seconds)
    return AudioOut(id=asset.id, url=url, content_type=asset.content_type)
