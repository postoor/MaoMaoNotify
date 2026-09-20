"""VoiceSynthesizer: synthesize+store and provider-failure fallback (§27, §30)."""

from datetime import UTC, datetime, timedelta

from app.core.config import settings
from app.models.audio import AudioAsset
from app.models.notification import Notification
from app.storage.memory import InMemoryStorage
from app.tts.base import AudioResult, TTSProvider, TTSProviderError
from app.tts.synthesizer import VoiceSynthesizer


class StubProvider(TTSProvider):
    name = "stub"

    async def synthesize(self, text, language=None, voice=None, options=None):
        return AudioResult(b"ID3-fake-mp3", "audio/mpeg", voice or "v", language, "stub")


class FailingProvider(TTSProvider):
    name = "failing"

    async def synthesize(self, text, language=None, voice=None, options=None):
        raise TTSProviderError(self.name, "boom")


async def _voice_notification(session, user_id):
    n = Notification(
        user_id=user_id,
        type="voice",
        message="部署完成",
        voice={"source": "server_tts", "language": "zh-TW"},
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(n)
    await session.flush()
    return n


async def test_synthesizes_stores_and_attaches(sessionmaker, create_user):
    user_id = await create_user("t@example.com")
    storage = InMemoryStorage()
    synth = VoiceSynthesizer(storage, settings, provider_factory=lambda name: StubProvider())

    async with sessionmaker() as s:
        n = await _voice_notification(s, user_id)
        await synth.apply(s, n, "部署完成")

        assert n.voice["audio_id"].startswith("audio_")
        assert n.voice["audio_url"].startswith("memory://")
        asset = await s.get(AudioAsset, n.voice["audio_id"])
        assert asset.source == "server_tts"
        assert asset.content_type == "audio/mpeg"
        assert asset.size == len(b"ID3-fake-mp3")
        assert await storage.get(asset.storage_key) == b"ID3-fake-mp3"


async def test_fallback_to_client_tts_on_failure(sessionmaker, create_user):
    user_id = await create_user("t@example.com")
    synth = VoiceSynthesizer(
        InMemoryStorage(), settings, provider_factory=lambda name: FailingProvider()
    )
    async with sessionmaker() as s:
        n = await _voice_notification(s, user_id)
        await synth.apply(s, n, "x")
        assert n.voice["source"] == "client_tts"
        assert n.voice["fallback_from"] == "server_tts"
        assert "audio_id" not in n.voice


async def test_no_fallback_records_error(sessionmaker, create_user):
    user_id = await create_user("t@example.com")
    no_fallback = settings.model_copy(update={"tts_fallback_provider": "none"})
    synth = VoiceSynthesizer(
        InMemoryStorage(), no_fallback, provider_factory=lambda name: FailingProvider()
    )
    async with sessionmaker() as s:
        n = await _voice_notification(s, user_id)
        await synth.apply(s, n, "x")
        assert n.voice.get("error") == "tts_provider_error"
        assert n.voice["source"] == "server_tts"  # unchanged
