"""Server-TTS synthesis for notifications (§27, §30).

Synthesizes voice notifications, stores the audio asset, and attaches
``audio_id`` / ``audio_url`` to the notification's ``voice`` payload. On provider
failure it falls back to ``client_tts`` (if configured) so the notification is
never blocked by a TTS failure (§30).
"""

from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import APIError
from app.models.audio import AudioAsset
from app.models.notification import Notification
from app.notifications import constants as c
from app.storage.base import StorageService
from app.tts.base import TTSProvider, TTSProviderError
from app.tts.registry import build_provider, resolve_provider_name


class VoiceSynthesizer:
    def __init__(
        self,
        storage: StorageService,
        settings: Settings,
        provider_factory: Callable[[str], TTSProvider] | None = None,
        default_provider: str | None = None,
    ):
        self.storage = storage
        self.settings = settings
        self.default_provider = default_provider  # admin runtime override (§29)
        self._factory = provider_factory or (lambda name: build_provider(name, settings))

    async def apply(self, session: AsyncSession, notification: Notification, text: str) -> None:
        voice = dict(notification.voice or {})
        requested = voice.get("provider")
        if requested in (None, "default") and self.default_provider:
            requested = self.default_provider
        name = resolve_provider_name(requested, self.settings)
        provider = self._factory(name)
        try:
            result = await provider.synthesize(
                text,
                language=voice.get("language"),
                voice=voice.get("voice"),
                options=voice,
            )
        except TTSProviderError:
            if self.settings.tts_fallback_provider == c.VOICE_CLIENT_TTS:
                notification.voice = {**voice, "source": c.VOICE_CLIENT_TTS,
                                      "fallback_from": c.VOICE_SERVER_TTS}
            else:
                notification.voice = {**voice, "error": "tts_provider_error"}
            return

        asset = AudioAsset(
            user_id=notification.user_id,
            source="server_tts",
            provider=result.provider,
            content_type=result.content_type,
            size=len(result.audio),
            storage_key="",
        )
        session.add(asset)
        await session.flush()
        key = f"audio/{asset.id}.{result.extension}"
        asset.storage_key = key
        await self.storage.put(key, result.audio, result.content_type)
        url = await self.storage.signed_url(key, self.settings.audio_url_ttl_seconds)
        notification.voice = {**voice, "audio_id": asset.id, "audio_url": url}

    async def attach_agent_audio(self, session: AsyncSession, notification: Notification) -> None:
        """Resolve an agent-uploaded audio_id → attach a signed download URL (§34)."""
        voice = dict(notification.voice or {})
        audio_id = voice.get("audio_id")
        if not audio_id:
            raise APIError("invalid_request", "voice.audio_id is required for agent_audio.", 400)
        asset = await session.get(AudioAsset, audio_id)
        if asset is None or asset.user_id != notification.user_id:
            raise APIError("invalid_request", "audio_id not found.", 400)
        size = await self.storage.stat(asset.storage_key)
        if size is None:
            raise APIError("invalid_request", "audio has not been uploaded yet.", 400)
        asset.size = size
        url = await self.storage.signed_url(asset.storage_key, self.settings.audio_url_ttl_seconds)
        notification.voice = {**voice, "audio_url": url}
